/**
 * contract-proxy - Supabase Edge Function for CORS-safe PDF proxying
 * 
 * Ported from DataDash implementation with adjustments for Orchestrate OS:
 * - MAX_CONTRACT_BYTES raised to 25MB (from 10MB) to match SRR cache limits
 * - Allowlist includes S3 buckets used by Ostereo data
 * - SSRF guard blocks private IPs
 * - Returns inline Content-Disposition (no download prompt)
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const MAX_CONTRACT_BYTES = 25 * 1024 * 1024; // 25MB

const ALLOWED_HOSTS = [
  "app-myautobots-public-dev.s3.amazonaws.com",
  "s3.amazonaws.com",
  "s3.us-east-1.amazonaws.com",
  "s3.us-west-2.amazonaws.com",
];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
  "Access-Control-Max-Age": "86400",
};

function isPrivateIP(hostname: string): boolean {
  const privatePatterns = [
    /^10\./,
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
    /^192\.168\./,
    /^127\./,
    /^169\.254\./,
    /^0\./,
    /^localhost$/i,
  ];
  return privatePatterns.some(p => p.test(hostname));
}

function isAllowedHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return ALLOWED_HOSTS.some(h => normalized === h || normalized.endsWith('.' + h));
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  const url = new URL(req.url);
  const contractUrl = url.searchParams.get("url");

  if (!contractUrl) {
    return new Response(JSON.stringify({ error: "Missing 'url' parameter" }), {
      status: 400,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(contractUrl);
  } catch {
    return new Response(JSON.stringify({ error: "Invalid URL" }), {
      status: 400,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  // SSRF guard
  if (isPrivateIP(parsedUrl.hostname)) {
    return new Response(JSON.stringify({ error: "Private IP not allowed" }), {
      status: 403,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  // Host allowlist
  if (!isAllowedHost(parsedUrl.hostname)) {
    return new Response(JSON.stringify({ 
      error: "Host not in allowlist",
      host: parsedUrl.hostname,
      allowed: ALLOWED_HOSTS,
    }), {
      status: 403,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  try {
    const response = await fetch(contractUrl, {
      method: req.method,
      redirect: "follow",
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ 
        error: "Upstream error",
        status: response.status,
      }), {
        status: 502,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    // Check Content-Length header
    const contentLength = response.headers.get("Content-Length");
    if (contentLength && parseInt(contentLength, 10) > MAX_CONTRACT_BYTES) {
      return new Response(JSON.stringify({ 
        error: "File too large",
        size: parseInt(contentLength, 10),
        limit: MAX_CONTRACT_BYTES,
      }), {
        status: 413,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    // Stream the response
    const body = await response.arrayBuffer();
    
    // Verify actual size
    if (body.byteLength > MAX_CONTRACT_BYTES) {
      return new Response(JSON.stringify({ 
        error: "File too large (actual)",
        size: body.byteLength,
        limit: MAX_CONTRACT_BYTES,
      }), {
        status: 413,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    // Extract filename from URL or Content-Disposition
    let filename = parsedUrl.pathname.split("/").pop() || "document.pdf";
    const upstreamDisposition = response.headers.get("Content-Disposition");
    if (upstreamDisposition) {
      const match = upstreamDisposition.match(/filename[*]?=['"]?([^'";]+)/i);
      if (match) filename = match[1];
    }

    const contentType = response.headers.get("Content-Type") || "application/pdf";

    return new Response(body, {
      status: 200,
      headers: {
        ...CORS_HEADERS,
        "Content-Type": contentType,
        "Content-Disposition": `inline; filename="${filename}"`,
        "Content-Length": body.byteLength.toString(),
        "X-Proxy-File-Size": body.byteLength.toString(),
        "X-Proxy-Source": "supabase-edge",
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return new Response(JSON.stringify({ error: "Fetch failed", message }), {
      status: 502,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }
});
