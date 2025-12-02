import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Define route patterns
const protectedRoutes = [
    '/dashboard',
    '/journal',
    '/signals',
    '/backtest',
    '/ai-analyst',
    '/settings',
];

const authRoutes = ['/login'];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Check if the current path is a protected route
    const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
    const isAuthRoute = authRoutes.some(route => pathname.startsWith(route));

    // Try to get token from cookies (future-proof for cookie-based auth)
    const tokenFromCookie = request.cookies.get('token')?.value;

    // For now, we rely on client-side localStorage, but middleware can't access it
    // So we use a hybrid approach: check cookie, and let client-side handle the rest
    // This middleware primarily handles cookie-based auth (when implemented)

    // If accessing protected route without cookie token, redirect to login
    // Note: This is a basic check. Client-side auth context will do the real validation
    if (isProtectedRoute && !tokenFromCookie) {
        // Allow the request to proceed - client-side will handle redirect if no localStorage token
        // This prevents double redirects and works with current localStorage-based auth
        return NextResponse.next();
    }

    // If accessing login page with valid token, redirect to dashboard
    if (isAuthRoute && tokenFromCookie) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    // Redirect root to dashboard if authenticated
    if (pathname === '/' && tokenFromCookie) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

// Configure which routes to run middleware on
export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - public folder
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\..*|api).*)',
    ],
};
