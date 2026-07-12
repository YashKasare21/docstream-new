import { SignJWT } from "jose";
import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

/**
 * Token proxy route.
 *
 * Decrypts the secure httpOnly NextAuth cookie (JWE-encrypted by next-auth v4)
 * and re-encodes the payload as a standard HS256 JWT that the FastAPI backend
 * can verify with PyJWT's ``jwt.decode(token, secret, algorithms=["HS256"])``.
 *
 * GET /api/auth/token
 *
 * Responses:
 *   200 — { "token": "<hs256-jwt>" }
 *   401 — { "error": "Not authenticated" }
 */
export async function GET(req: NextRequest) {
  const payload = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET,
    raw: false,
  });

  if (!payload) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const secretKey = new TextEncoder().encode(process.env.NEXTAUTH_SECRET);

  const jwt = await new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(secretKey);

  return NextResponse.json({ token: jwt });
}
