"""
PDF Proxy Service for Orchestrate OS

A lightweight FastAPI proxy that fetches PDFs from allowlisted hosts and serves
them with proper headers to avoid CORS issues and download prompts.

Usage:
    uvicorn pdf_proxy:app --host 0.0.0.0 --port 8000

Environment Variables:
    PDF_PROXY_ALLOWED_HOSTS: Comma-separated list of allowed hostnames
        Default: app-myautobots-public-dev.s3.amazonaws.com
    PDF_PROXY_ALLOWED_ORIGINS: CORS allowed origins (comma-separated)
        Default: * (all origins)
    PDF_PROXY_MAX_SIZE_MB: Maximum file size in MB
        Default: 25
"""

import os
import ipaddress
import socket
from urllib.parse import urlparse, unquote
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(
    title="Orchestrate OS PDF Proxy",
    description="CORS-safe PDF proxy for Single Row Review",
    version="1.0.0"
)

DEFAULT_ALLOWED_HOSTS = [
    "app-myautobots-public-dev.s3.amazonaws.com",
    "s3.amazonaws.com",
    "s3.us-east-1.amazonaws.com",
    "s3.us-west-2.amazonaws.com",
]

ALLOWED_HOSTS = os.environ.get(
    "PDF_PROXY_ALLOWED_HOSTS",
    ",".join(DEFAULT_ALLOWED_HOSTS)
).split(",")
ALLOWED_HOSTS = [h.strip().lower() for h in ALLOWED_HOSTS if h.strip()]

ALLOWED_ORIGINS = os.environ.get("PDF_PROXY_ALLOWED_ORIGINS", "*").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

MAX_SIZE_MB = int(os.environ.get("PDF_PROXY_MAX_SIZE_MB", "25"))
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "X-Proxy-Source"],
)


@app.options("/proxy/pdf")
async def proxy_pdf_options():
    """Explicit OPTIONS handler for CORS preflight."""
    from fastapi.responses import Response
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP (SSRF guard)."""
    try:
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
    except (socket.gaierror, ValueError):
        return True


def is_host_allowed(hostname: str) -> bool:
    """Check if hostname is in the allowlist."""
    hostname_lower = hostname.lower()
    for allowed in ALLOWED_HOSTS:
        if hostname_lower == allowed or hostname_lower.endswith("." + allowed):
            return True
    return False


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "allowed_hosts": ALLOWED_HOSTS}


@app.get("/proxy/pdf")
async def proxy_pdf(url: str = Query(..., description="URL of the PDF to fetch")):
    """
    Fetch a PDF from an allowlisted host and return it with inline disposition.
    
    Security:
    - Only allowlisted hosts are permitted
    - Private IPs are blocked (SSRF guard)
    - Size limit enforced via Content-Length
    """
    try:
        decoded_url = unquote(url)
        parsed = urlparse(decoded_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs allowed")
    
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Missing hostname in URL")
    
    if not is_host_allowed(hostname):
        raise HTTPException(
            status_code=403,
            detail=f"Host not in allowlist: {hostname}"
        )
    
    if is_private_ip(hostname):
        raise HTTPException(
            status_code=403,
            detail="Private/reserved IPs are blocked"
        )
    
    # v1.4.16: Disable redirects and validate final URL for SSRF protection
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        try:
            # First check size via HEAD (if available)
            try:
                head_resp = await client.head(decoded_url)
                content_length = head_resp.headers.get("content-length")
                
                if content_length:
                    size = int(content_length)
                    if size > MAX_SIZE_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large: {size} bytes (max {MAX_SIZE_BYTES})"
                        )
                
                # Handle redirects manually with SSRF validation
                if head_resp.status_code in (301, 302, 303, 307, 308):
                    redirect_url = head_resp.headers.get("location")
                    if redirect_url:
                        redirect_parsed = urlparse(redirect_url)
                        redirect_host = redirect_parsed.hostname
                        if not redirect_host or not is_host_allowed(redirect_host) or is_private_ip(redirect_host):
                            raise HTTPException(status_code=403, detail="Redirect to non-allowlisted host blocked")
                        decoded_url = redirect_url
            except httpx.HTTPStatusError:
                pass  # Some servers don't support HEAD
            
            # Stream response with size enforcement
            resp = await client.get(decoded_url)
            
            # Handle redirects on GET as well
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_url = resp.headers.get("location")
                if redirect_url:
                    redirect_parsed = urlparse(redirect_url)
                    redirect_host = redirect_parsed.hostname
                    if not redirect_host or not is_host_allowed(redirect_host) or is_private_ip(redirect_host):
                        raise HTTPException(status_code=403, detail="Redirect to non-allowlisted host blocked")
                    resp = await client.get(redirect_url)
            
            resp.raise_for_status()
            
            # Enforce size limit on actual content
            if len(resp.content) > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Response too large: {len(resp.content)} bytes (max {MAX_SIZE_BYTES})"
                )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Upstream timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Upstream error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")
    
    content_type = resp.headers.get("content-type", "application/pdf")
    
    filename = parsed.path.split("/")[-1] or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
            "X-Proxy-Source": hostname,
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
