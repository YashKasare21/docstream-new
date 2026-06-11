import NextAuth, { AuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

/**
 * NextAuth configuration.
 *
 * Real Google OAuth — requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
 * environment variables. The JWT is signed with HS256 using NEXTAUTH_SECRET.
 *
 * Token proxy: the frontend reads the httpOnly cookie via /api/auth/token
 * to obtain the raw JWT for authenticating against the FastAPI backend.
 */
export const authOptions: AuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  },
  jwt: {
    maxAge: 60 * 60 * 24 * 30,
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, profile }) {
      if (profile) {
        token.email = profile.email;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.email = token.email as string;
      }
      return session;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
