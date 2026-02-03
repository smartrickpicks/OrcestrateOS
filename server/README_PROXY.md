# PDF Proxy Services

PDF proxying for Single Row Review (SRR) to avoid CORS issues and browser download prompts.

## Proxy Options

The SRR panel supports two proxy backends:

| Priority | Proxy | When Used |
|----------|-------|-----------|
| 1 (Primary) | **Supabase Edge Function** | If `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set |
| 2 (Fallback) | **FastAPI** | Otherwise, auto-detected in Replit environment |

### Supabase Edge Function (Recommended)

Location: `supabase/functions/contract-proxy/index.ts`

Endpoint: `${VITE_SUPABASE_URL}/functions/v1/contract-proxy?url=<encoded-url>`

Required env vars:
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anon/public key

### FastAPI Proxy (Fallback)

A lightweight FastAPI proxy that fetches PDFs from allowlisted S3 buckets and serves them with proper headers.

## Purpose

When the Single Row Review (SRR) panel attempts to display a PDF from an external source (e.g., S3), browsers enforce CORS restrictions and may trigger a download prompt instead of inline rendering. Both proxies:

1. Fetches the PDF server-side (bypassing CORS)
2. Returns it with `Content-Disposition: inline` (no download prompt)
3. Preserves the original `Content-Type`
4. Adds cache headers for performance

## Quick Start

```bash
cd server
pip install -r requirements.txt
uvicorn pdf_proxy:app --host 0.0.0.0 --port 8000
```

## API

### `GET /proxy/pdf?url=<encoded-url>`

Fetch and proxy a PDF from an allowlisted host.

**Query Parameters:**
- `url` (required): URL-encoded path to the PDF

**Response:**
- `200 OK`: PDF content with `Content-Type: application/pdf` and `Content-Disposition: inline`
- `403 Forbidden`: Host not in allowlist or private IP detected
- `413 Payload Too Large`: File exceeds size limit
- `502/504`: Upstream fetch error or timeout

### `GET /health`

Health check endpoint. Returns allowed hosts list.

## Security

### Redirect Validation (v1.4.16)

The proxy validates redirects to prevent SSRF attacks:
- Redirects are not automatically followed
- Each redirect URL is validated against the allowlist
- Private IPs are blocked even in redirect targets

### Response Size Enforcement

Size limits are enforced at two points:
1. Via `Content-Length` header (pre-flight check)
2. After download (actual content size validation)

### Host Allowlist

Only PDFs from explicitly allowlisted hosts are permitted. Set via environment variable:

```bash
export PDF_PROXY_ALLOWED_HOSTS="app-myautobots-public-dev.s3.amazonaws.com,s3.amazonaws.com"
```

Default allowlist:
- `app-myautobots-public-dev.s3.amazonaws.com`
- `s3.amazonaws.com`
- `s3.us-east-1.amazonaws.com`
- `s3.us-west-2.amazonaws.com`

### SSRF Protection

Private and reserved IP ranges are blocked:
- 10.x.x.x, 172.16-31.x.x, 192.168.x.x
- 127.x.x.x (localhost)
- Link-local, multicast, etc.

### Size Limit

Default: 25 MB. Configure via:

```bash
export PDF_PROXY_MAX_SIZE_MB=50
```

## Dev Environment Config

For local Replit development, the proxy is pre-configured with sensible defaults:

```bash
# Allow all viewer origins (default for dev)
PDF_PROXY_ALLOWED_ORIGINS=*

# S3 bucket for Ostereo test data
PDF_PROXY_ALLOWED_HOSTS=app-myautobots-public-dev.s3.amazonaws.com
```

The viewer auto-detects the Replit domain and constructs the correct port 8000 proxy URL.

### CORS

Configure allowed origins:

```bash
export PDF_PROXY_ALLOWED_ORIGINS="http://localhost:5000,https://yourapp.replit.app"
```

Default: `*` (all origins)

## Integration with Viewer

The viewer (`ui/viewer/index.html`) automatically routes PDF loads through this proxy when available. Configure the proxy base URL:

```javascript
var PDF_PROXY_BASE_URL = 'http://localhost:8000/proxy/pdf';
```

If the proxy is unreachable, the viewer shows a "Proxy unavailable" message.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PDF_PROXY_ALLOWED_HOSTS` | S3 domains | Comma-separated allowlist |
| `PDF_PROXY_ALLOWED_ORIGINS` | `*` | CORS origins |
| `PDF_PROXY_MAX_SIZE_MB` | `25` | Max file size in MB |
