export const config = {
  runtime: "nodejs"
};

export default async function handler(request) {
  const backendUrl = process.env.RENDER_BACKEND_URL;
  if (!backendUrl) {
    return new Response("RENDER_BACKEND_URL is not configured", { status: 503 });
  }

  const url = new URL(request.url);
  const proxiedPath = url.searchParams.get("path");
  const originalPath = proxiedPath ? `/${proxiedPath}` : url.pathname;
  url.searchParams.delete("path");
  const target = new URL(originalPath + url.search, backendUrl);
  const headers = new Headers(request.headers);
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-Proto", "https");

  let body;
  if (!["GET", "HEAD"].includes(request.method)) {
    body = await request.arrayBuffer();
  }

  const response = await fetch(target, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}
