import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

const backendUrl = () => process.env.BACKEND_API_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: RouteContext, method: string) {
  const { path } = await context.params;
  const route = path.map((segment) => encodeURIComponent(segment)).join("/");
  if (route === "auth/logout") {
    (await cookies()).delete("outreachos_session");
    return NextResponse.json({ ok: true });
  }

  const isAuth = route === "auth/login" || route === "auth/signup";
  const isPublic = isAuth || route === "unsubscribe";
  const cookieStore = await cookies();
  const token = cookieStore.get("outreachos_session")?.value;
  if (!isPublic && !token) {
    return NextResponse.json({ detail: "Please sign in." }, { status: 401 });
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (token) headers.set("authorization", `Bearer ${token}`);
  const url = `${backendUrl()}/${route}${request.nextUrl.search}`;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();
  let upstream: Response;
  try {
    upstream = await fetch(url, { method, headers, body, cache: "no-store" });
  } catch {
    return NextResponse.json({ detail: "The API is unavailable. Check that the backend is running." }, { status: 502 });
  }

  const responseBody = await upstream.text();
  if (isAuth && upstream.ok) {
    const data = JSON.parse(responseBody) as {
      access_token: string;
      org_id: number;
      org_name: string;
      user_id: number;
    };
    const response = NextResponse.json({
      org_id: data.org_id,
      org_name: data.org_name,
      user_id: data.user_id,
    }, { status: upstream.status });
    response.cookies.set("outreachos_session", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60,
    });
    return response;
  }

  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "GET");
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "POST");
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "PUT");
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "PATCH");
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "DELETE");
}
