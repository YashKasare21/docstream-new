"use client";

import { Star, Copy, Check } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

export default function OpenSource() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText("pip install docstream");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="open-source" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6 }}
        className="gradient-border p-8 text-center"
      >
        <div className="relative z-10">
          {/* Title */}
          <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
            Proudly Open Source
          </h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Docstream is MIT licensed. Use it, fork it, contribute to it. The
            library is published on PyPI and used by developers worldwide.
          </p>

          {/* Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl border border-slate-700 hover:border-slate-600 transition-all duration-200"
            >
              <Star className="w-4 h-4 text-yellow-400" />
              Star on GitHub
            </a>

            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-3 bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 font-mono text-sm text-green-400 cursor-pointer hover:border-green-500/30 hover:bg-black/60 transition-all duration-200"
            >
              <span className="text-slate-400">$</span>
              pip install docstream
              {copied ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-slate-400" />
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
