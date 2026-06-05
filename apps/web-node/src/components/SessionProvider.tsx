"use client";

import { SessionProvider as NextAuthSessionProvider } from "next-auth/react";
import { ReactNode } from "react";

/**
 * Thin client wrapper around NextAuth's ``SessionProvider`` so the
 * root layout can stay a server component.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  return (
    <NextAuthSessionProvider>{children}</NextAuthSessionProvider>
  );
}
