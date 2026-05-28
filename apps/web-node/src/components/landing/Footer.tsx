import { FileCode } from "lucide-react";
import Link from "next/link";

export default function Footer() {
  const links = [
    { label: "GitHub", href: "https://github.com", external: true },
    { label: "PyPI", href: "https://pypi.org", external: true },
    { label: "Documentation", href: "#", external: false },
    { label: "Contributing", href: "#", external: false },
  ];

  return (
    <footer className="border-t border-slate-800 bg-[#020617] py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-8">
        {/* Logo and tagline */}
        <div className="flex flex-col items-center md:items-start gap-2">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-blue-500" />
            <span className="font-bold text-white">Docstream</span>
          </div>
          <span className="text-slate-600 text-sm">
            AI-powered PDF to LaTeX conversion
          </span>
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center justify-center gap-6">
          {links.map((link) =>
            link.external ? (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-slate-500 hover:text-white transition-colors duration-200"
              >
                {link.label}
              </a>
            ) : (
              <Link
                key={link.label}
                href={link.href}
                className="text-sm text-slate-500 hover:text-white transition-colors duration-200"
              >
                {link.label}
              </Link>
            )
          )}
        </div>

        {/* Copyright */}
        <p className="text-sm text-slate-600">
          © 2025 Docstream. MIT License.
        </p>
      </div>
    </footer>
  );
}
