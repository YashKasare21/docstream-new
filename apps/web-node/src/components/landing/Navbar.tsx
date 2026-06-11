"use client";

import { useState, useEffect } from "react";
import { FileCode, Menu, X, Zap, Moon, Sun, LogIn, LogOut, History, CreditCard } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/lib/theme-provider";
import { useSession, signIn, signOut } from "next-auth/react";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const isAuthenticated = status === "authenticated";
  const userEmail = session?.user?.email ?? null;

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { label: "Features", href: "/#features" },
    { label: "Templates", href: "/#how-it-works" },
    { label: "Docs", href: "/#open-source" },
  ];

  const isLanding = pathname === "/";

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-background/60 backdrop-blur-xl border-b border-border py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="relative">
              <FileCode className="w-6 h-6 text-blue-500 transition-transform group-hover:scale-110" />
              <Zap className="w-3 h-3 text-yellow-400 absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <span className="font-bold text-xl tracking-tight text-foreground hover:text-blue-400 transition-colors duration-200 cursor-pointer">
              Docstream
            </span>
          </Link>

          {/* Desktop navigation */}
          <div className="hidden md:flex items-center gap-6">
            {isLanding &&
              navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-muted-foreground hover:text-foreground transition-colors duration-200 text-sm relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-px after:bg-blue-400 hover:after:w-full after:transition-all after:duration-300"
                >
                  {link.label}
                </a>
              ))}
            <a
              href="https://github.com/YashKasare21/docstream-new"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-muted-foreground border border-border hover:border-blue-500/40 px-4 py-2 rounded-lg transition-all duration-200 hover:text-foreground"
            >
              GitHub
            </a>
            {!isLanding && (
              <Link
                href="/"
                className="text-sm font-medium text-muted-foreground border border-border hover:border-blue-500/40 px-4 py-2 rounded-lg transition-all duration-200 hover:text-foreground"
              >
                Home
              </Link>
            )}
            <Link
              href="/convert"
              className="shimmer-btn bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
            >
              Convert PDF
            </Link>
            {/* History link — only when signed in */}
            {isAuthenticated && (
              <>
                <Link
                  href="/history"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-200 inline-flex items-center gap-1"
                >
                  <History className="w-4 h-4" />
                  History
                </Link>
                <Link
                  href="/billing"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-200 inline-flex items-center gap-1"
                >
                  <CreditCard className="w-4 h-4" />
                  Billing
                </Link>
              </>
            )}
            {/* Auth controls */}
            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <span
                  className="text-xs text-muted-foreground max-w-[140px] truncate"
                  title={userEmail ?? ""}
                >
                  {userEmail}
                </span>
                <button
                  onClick={() => signOut({ callbackUrl: "/" })}
                  className="text-sm font-medium text-muted-foreground border border-border hover:border-blue-500/40 px-3 py-2 rounded-lg transition-all duration-200 hover:text-foreground inline-flex items-center gap-1"
                  aria-label="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => signIn(undefined, { callbackUrl: "/convert" })}
                className="text-sm font-medium text-foreground border border-blue-500/40 hover:bg-blue-500/10 px-3 py-2 rounded-lg transition-all duration-200 inline-flex items-center gap-1"
                aria-label="Sign in"
              >
                <LogIn className="w-4 h-4" />
                Sign In
              </button>
            )}
            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-all duration-200"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>

          {/* Mobile hamburger + theme */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-all duration-200"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border overflow-hidden"
          >
            <div className="px-4 py-6 space-y-4">
              {isLanding &&
                navLinks.map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
                  >
                    {link.label}
                  </a>
                ))}
              <div className="pt-4 flex flex-col gap-3">
                <a
                  href="https://github.com/YashKasare21/docstream-new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-muted-foreground border border-border px-4 py-2 rounded-lg text-center hover:text-foreground hover:border-blue-500/40 transition-all"
                >
                  GitHub
                </a>
                <Link
                  href="/convert"
                  onClick={() => setMobileMenuOpen(false)}
                  className="shimmer-btn bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-center text-sm font-medium transition-colors duration-200"
                >
                  Convert PDF
                </Link>
                {isAuthenticated && (
                  <Link
                    href="/history"
                    onClick={() => setMobileMenuOpen(false)}
                    className="text-sm text-muted-foreground hover:text-foreground py-2 inline-flex items-center justify-center gap-2"
                  >
                    <History className="w-4 h-4" />
                    History
                  </Link>
                )}
                {isAuthenticated ? (
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      signOut({ callbackUrl: "/" });
                    }}
                    className="text-sm text-muted-foreground border border-border px-4 py-2 rounded-lg hover:text-foreground hover:border-blue-500/40 transition-all inline-flex items-center justify-center gap-2"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out ({userEmail})
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      signIn(undefined, { callbackUrl: "/convert" });
                    }}
                    className="text-sm text-foreground border border-blue-500/40 px-4 py-2 rounded-lg hover:bg-blue-500/10 transition-all inline-flex items-center justify-center gap-2"
                  >
                    <LogIn className="w-4 h-4" />
                    Sign In
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
