import NextAuth, { AuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

/**
 * NextAuth configuration.
 *
 * Demo-only Credentials provider — any non-empty email is accepted.
 * In a real deployment swap this for OAuth or a backed user store
 * (and a real password hash check).
 */
export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Email",
      credentials: {
        email: {
          label: "Email",
          type: "email",
          placeholder: "you@example.com",
        },
      },
      async authorize(credentials) {
        const email = credentials?.email?.trim();
        if (!email) {
          return null;
        }
        return {
          id: email,
          email,
          name: email,
        };
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = (user as { id?: string }).id ?? user.email ?? token.sub;
        token.email = user.email ?? token.email ?? undefined;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as { id?: string }).id =
          (token as { id?: string }).id ??
          token.sub ??
          session.user.email ??
          undefined;
      }
      return session;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
