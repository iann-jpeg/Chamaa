export const config = {
  runtime: "nodejs"
};

export default async function handler(request) {
  try {
    const backendUrl =
      process.env.RENDER_BACKEND_URL || "https://chamaa-6kzn.onrender.com";
    const url = new URL(request.url);
    const proxiedPath = url.searchParams.get("path");
    const originalPath = proxiedPath ? `/${proxiedPath}` : url.pathname;
    url.searchParams.delete("path");
    const target = new URL(originalPath + url.search, backendUrl);

    const headers = new Headers();
    const forwardedHeaders = [
      "accept",
      "accept-language",
      "content-type",
      "cookie",
      "referer",
      "user-agent",
      "x-requested-with",
    ];
    for (const name of forwardedHeaders) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    headers.set("Origin", url.origin);
    headers.set("Referer", url.origin + originalPath);
    headers.set("X-Forwarded-Host", url.host);
    headers.set("X-Forwarded-Proto", "https");

    const body =
      ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer();

    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    for (const name of [
      "cache-control",
      "content-type",
      "expires",
      "location",
      "vary",
    ]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }

    const setCookie =
      typeof response.headers.getSetCookie === "function"
        ? response.headers.getSetCookie()
        : [response.headers.get("set-cookie")].filter(Boolean);
    for (const cookie of setCookie) {
      responseHeaders.append("set-cookie", cookie);
    }

    const location = responseHeaders.get("location");
    if (location?.startsWith("/")) {
      responseHeaders.set("location", new URL(location, url.origin).toString());
    }

    const responseBody =
      request.method === "HEAD" ? null : await response.arrayBuffer();
    return new Response(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    return new Response("Backend proxy unavailable", {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
}
