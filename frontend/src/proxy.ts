import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTHENTICATED_REDIRECT_ROUTES = new Set(["/login", "/signup"]);

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const sessionId = request.cookies.get("sessionid")?.value;
  const isAuthenticated = Boolean(sessionId);

  if (pathname.startsWith("/dashboard") && !isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname + search);
    return NextResponse.redirect(loginUrl);
  }

  if (AUTHENTICATED_REDIRECT_ROUTES.has(pathname) && isAuthenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
