import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

const ALLOWED_HOSTS = [
  "app-myautobots-public-dev.s3.amazonaws.com",
];

const MAX_CONTRACT_BYTES = 25 * 1024 * 1024;
const FETCH_TIMEOUT_MS = 30000;

const PRIVATE_IP_RANGES = [
  /^127\./,
  /^10\./,
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
  /^192\.168\./,
  /^0\./,
  /^169\.254\./,
  /^::1$/,
  /^fc00:/i,
  /^fe80:/i,
];

const ALLOWED_CONTENT_TYPES = [
  "application/pdf",
  "application/octet-stream",
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const PDF_MAGIC_BYTES = [0x25, 0x50, 0x44, 0x46];

type ProxyErrorCode =
  | "invalid_url"
  | "host_not_allowed"
  | "blocked_private_network"
  | "http_error"
  | "file_too_large"
  | "not_supported_type"
  | "network_error"
  | "timeout";

interface ProxyErrorResponse {
  error: true;
  code: ProxyErrorCode;
  message: string;
  httpStatus?: number;
  fileSize?: number;
}

function isPrivateNetwork(hostname: string): boolean {
  if (hostname === "localhost") return true;
  for (const pattern of PRIVATE_IP_RANGES) {
    if (pattern.test(hostname)) return true;
  }
  return false;
}

function isHostAllowed(hostname: string): boolean {
  return ALLOWED_HOSTS.some((allowed) => {
    if (allowed.startsWith("*.")) {
      const suffix = allowed.slice(1);
      return hostname.endsWith(suffix) || hostname === allowed.slice(2);
    }
    return hostname === allowed;
  });
}

function isPdfSignature(bytes: Uint8Array): boolean {
  if (bytes.length < 4) return false;
  return PDF_MAGIC_BYTES.every((b, i) => bytes[i] === b);
}

function isAllowedContentType(contentType: string | null): boolean {
  if (!contentType) return false;
  const lower = contentType.toLowerCase();
  return ALLOWED_CONTENT_TYPES.some((allowed) => lower.includes(allowed));
}

function errorResponse(
  code: ProxyErrorCode,
  message: string,
  extra: Partial<ProxyErrorResponse> = {}
): Response {
  const body: ProxyErrorResponse = {
    error: true,
    code,
    message,
    ...extra,
  };
  return new Response(JSON.stringify(body), {
    status: code === "file_too_large" ? 413 : code === "http_error" ? 502 : 400,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  if (req.method !== "GET") {
    return errorResponse("invalid_url", "Only GET requests are allowed");
  }

  const requestUrl = new URL(req.url);
  const targetUrlParam = requestUrl.searchParams.get("url");

  if (!targetUrlParam) {
    return errorResponse("invalid_url", "Missing 'url' query parameter");
  }

  let targetUrl: URL;
  try {
    targetUrl = new URL(targetUrlParam);
  } catch {
    return errorResponse("invalid_url", "Invalid URL format");
  }

  if (!["http:", "https:"].includes(targetUrl.protocol)) {
    return errorResponse("invalid_url", "Only http and https protocols are allowed");
  }

  if (isPrivateNetwork(targetUrl.hostname)) {
    return errorResponse("blocked_private_network", "Access to private networks is blocked");
  }

  if (!isHostAllowed(targetUrl.hostname)) {
    return errorResponse("host_not_allowed", `Host '${targetUrl.hostname}' is not in the allowlist`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    const response = await fetch(targetUrl.toString(), {
      signal: controller.signal,
      headers: {
        "User-Agent": "OrchestrateOS-ContractProxy/1.0",
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return errorResponse("http_error", `Remote server returned ${response.status}`, {
        httpStatus: response.status,
      });
    }

    const contentType = response.headers.get("content-type");
    const contentLength = response.headers.get("content-length");
    const contentDisposition = response.headers.get("content-disposition");
    const declaredSize = contentLength ? parseInt(contentLength, 10) : null;

    if (declaredSize && declaredSize > MAX_CONTRACT_BYTES) {
      return errorResponse(
        "file_too_large",
        `File size ${(declaredSize / 1024 / 1024).toFixed(1)} MB exceeds limit of ${MAX_CONTRACT_BYTES / 1024 / 1024} MB`,
        { fileSize: declaredSize }
      );
    }

    const reader = response.body?.getReader();
    if (!reader) {
      return errorResponse("network_error", "Failed to read response body");
    }

    const chunks: Uint8Array[] = [];
    let totalBytes = 0;
    let firstChunk = true;
    let validatedType = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      totalBytes += value.length;

      if (totalBytes > MAX_CONTRACT_BYTES) {
        reader.cancel();
        return errorResponse(
          "file_too_large",
          `File exceeds size limit of ${MAX_CONTRACT_BYTES / 1024 / 1024} MB`,
          { fileSize: totalBytes }
        );
      }

      if (firstChunk) {
        firstChunk = false;
        const isPdf = isPdfSignature(value);
        const isAllowedType = isAllowedContentType(contentType);

        if (!isPdf && !isAllowedType) {
          reader.cancel();
          return errorResponse(
            "not_supported_type",
            `Content type '${contentType || "unknown"}' is not supported`
          );
        }
        validatedType = true;
      }

      chunks.push(value);
    }

    if (!validatedType && chunks.length === 0) {
      return errorResponse("network_error", "Empty response from remote server");
    }

    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const body = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.length;
    }

    const responseHeaders: Record<string, string> = {
      ...corsHeaders,
      "Content-Length": totalLength.toString(),
      "Cache-Control": "no-store",
      "X-Proxy-File-Size": totalLength.toString(),
    };

    if (contentType) {
      responseHeaders["Content-Type"] = contentType;
    }

    if (contentDisposition) {
      responseHeaders["Content-Disposition"] = contentDisposition;
    } else {
      responseHeaders["Content-Disposition"] = "inline";
    }

    return new Response(body, {
      status: 200,
      headers: responseHeaders,
    });
  } catch (err) {
    clearTimeout(timeoutId);

    if (err instanceof Error) {
      if (err.name === "AbortError") {
        return errorResponse("timeout", "Request timed out after 30 seconds");
      }
      return errorResponse("network_error", `Network error: ${err.message}`);
    }

    return errorResponse("network_error", "Unknown network error occurred");
  }
});
