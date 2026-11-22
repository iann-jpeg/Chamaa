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

  const headers = new Headers();
  for (const name of [
    "accept",
    "accept-language",
    "content-type",
    "cookie",
    "origin",
    "referer",
    "user-agent",
    "x-requested-with",
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
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

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  const setCookies =
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : [response.headers.get("set-cookie")].filter(Boolean);
  for (const cookie of setCookies) {
    responseHeaders.append("set-cookie", cookie);
  }

  const location = responseHeaders.get("location");
  if (location?.startsWith("/")) {
    responseHeaders.set("location", new URL(location, url.origin).toString());
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}
