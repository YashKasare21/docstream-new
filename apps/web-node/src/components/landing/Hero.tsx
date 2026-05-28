"use client";

import { useRef } from "react";
import { ArrowRight, FileText, CheckCircle, Zap } from "lucide-react";
import { motion, useMotionValue, animate } from "framer-motion";

const PARTICLES = [
  { top: "8%",  left: "-10px" },
  { top: "35%", right: "-10px" },
  { top: "65%", left: "-14px" },
  { bottom: "12%", right: "-12px" },
  { top: "-10px", left: "25%" },
  { bottom: "-10px", right: "30%" },
];

export default function Hero() {
  const cardRef = useRef<HTMLDivElement>(null);
  const rotateX = useMotionValue(0);
  const rotateY = useMotionValue(0);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    rotateX.set(y * -10);
    rotateY.set(x * 10);
  };

  const handleMouseLeave = () => {
    animate(rotateX, 0, { duration: 0.5 });
    animate(rotateY, 0, { duration: 0.5 });
  };

  return (
    <section
      className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-12 lg:pt-36 lg:pb-24 grid lg:grid-cols-2 gap-16 items-center"
    >
      {/* Dot-grid background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          backgroundImage: "radial-gradient(#1E3A5F 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 50%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 50%, transparent 100%)",
        }}
      />
      <div className="absolute inset-0 dot-grid opacity-40 pointer-events-none -z-10" aria-hidden="true" />

      {/* Left column — copy */}
      <div className="space-y-8">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 glass-card px-4 py-1.5 text-xs text-blue-300 border border-blue-500/20 mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          ⭐ Open Source · PyPI Published · MIT License
        </motion.div>

        {/* Heading */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1]"
        >
          <span className="text-white">Turn PDFs into</span>
          <br />
          <span className="bg-gradient-to-r from-blue-400 via-blue-300 to-purple-400 bg-clip-text text-transparent">
            Perfect LaTeX
          </span>
        </motion.h1>

        {/* Subtext */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg lg:text-xl text-slate-400 leading-relaxed max-w-xl"
        >
          Upload your research papers, theses, or proof-heavy documents. Our
          AI-powered pipeline extracts structure, formulas, and citations into
          publication-quality LaTeX in minutes.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-wrap gap-4"
        >
          <a
            href="#upload"
            className="shimmer-btn bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] transition-all duration-300"
          >
            Start Converting Free
            <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 rounded-xl border border-white/10 text-slate-300 hover:border-white/20 hover:text-white hover:bg-white/5 flex items-center gap-2 transition-all duration-200"
          >
            View on GitHub
          </a>
        </motion.div>
      </div>

      {/* Right column — 3D perspective container */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.2 }}
        className="relative flex items-center justify-center"
        style={{ perspective: "1000px" }}
      >
        {/* Background glow */}
        <div className="absolute inset-0 bg-blue-500/10 blur-[100px] rounded-full" />

        {/* Floating particles */}
        {PARTICLES.map((pos, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-blue-400/40 pointer-events-none"
            style={pos}
            animate={{ y: [0, -12, 0], opacity: [0.4, 0.8, 0.4] }}
            transition={{ duration: 3 + i, repeat: Infinity, delay: i * 0.5, ease: "easeInOut" }}
          />
        ))}

        {/* Tiltable card group */}
        <motion.div
          ref={cardRef}
          style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="cursor-pointer relative w-full max-w-md aspect-square bg-slate-900/50 border border-slate-800 rounded-3xl p-8 backdrop-blur-sm overflow-hidden"
        >
          <div className="h-full flex flex-col justify-between">
            {/* PDF card */}
            <div className="glass-card p-4 flex items-center justify-between animate-float">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-500/20 border border-red-500/30 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    paper_draft.pdf
                  </p>
                  <p className="text-xs text-slate-500">2.4 MB</p>
                </div>
              </div>
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>

            {/* Pulsing horizontal arrow animation */}
            <div className="flex justify-center items-center my-4 gap-2">
              <div className="h-[1px] w-12 bg-gradient-to-r from-transparent to-blue-500" />
              <motion.div
                animate={{ x: [0, 8, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              >
                <Zap className="w-6 h-6 text-blue-400" />
              </motion.div>
              <div className="h-[1px] w-12 bg-gradient-to-l from-transparent to-indigo-500" />
            </div>

            {/* LaTeX output card */}
            <div className="glass-card p-4 font-mono text-xs">
              <div className="flex items-center gap-1.5 mb-3 pb-2 border-b border-white/10">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
                <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
                <span className="ml-2 text-slate-500 text-xs">main.tex</span>
              </div>
              <div className="space-y-1.5 opacity-70">
                <div className="text-slate-400">
                  <span className="text-blue-400">\documentclass</span>
                  {"{article}"}
                </div>
                <div className="text-slate-400">
                  <span className="text-purple-400">\usepackage</span>
                  {"{amsmath}"}
                </div>
                <div className="text-slate-400">
                  <span className="text-green-400">\begin</span>
                  {"{document}"}
                </div>
                <div className="text-slate-300 pl-4">
                  <span className="text-yellow-300">{"$E = mc^2$"}</span>
                </div>
                <div className="text-slate-400">
                  <span className="text-green-400">\end</span>
                  {"{document}"}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
