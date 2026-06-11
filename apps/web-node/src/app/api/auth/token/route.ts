import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

/**
 * Token proxy route.
 *
 * Reads the secure httpOnly NextAuth cookie and returns the raw JWT
 * string. The frontend client calls this endpoint to obtain the JWT
 * needed for authenticating against the FastAPI backend via the
 * ``Authorization: Bearer <token>`` header.
 *
 * GET /api/auth/token
 *
 * Responses:
 *   200 — { "token": "<raw-jwt>" }
 *   401 — { "error": "Not authenticated" }
 */
export async function GET(req: NextRequest) {
  const rawToken = await getToken({ req, secret: process.env.NEXTAUTH_SECRET, raw: true });
  if (!rawToken) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }
  return NextResponse.json({ token: rawToken });
}
