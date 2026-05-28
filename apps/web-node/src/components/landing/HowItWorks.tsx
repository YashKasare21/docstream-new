"use client";

import { Upload, LayoutTemplate, Download } from "lucide-react";
import { motion } from "framer-motion";

const steps = [
  {
    number: "01",
    icon: Upload,
    title: "Upload PDF",
    description: "Drag & drop or click to browse. Supports scanned and digital PDFs up to 50 MB.",
  },
  {
    number: "02",
    icon: LayoutTemplate,
    title: "Choose Template",
    description: "Select from Report, IEEE, or Resume formats. Each template is meticulously crafted.",
  },
  {
    number: "03",
    icon: Download,
    title: "Download Output",
    description: "Get your .tex source file along with a compiled .pdf — ready for submission.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5 }}
        className="text-center mb-16"
      >
        <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
          How it works
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Three simple steps to convert your PDF into publication-quality LaTeX
        </p>
      </motion.div>

      <div className="relative">
        {/* Connecting line — horizontal on desktop, vertical on mobile */}
        <div className="hidden md:block absolute top-16 left-[16.67%] right-[16.67%] h-[2px] bg-gradient-to-r from-blue-500/20 via-blue-500/40 to-blue-500/20" />
        <div className="md:hidden absolute left-8 top-0 bottom-0 w-[2px] bg-gradient-to-b from-blue-500/20 via-blue-500/40 to-blue-500/20" />

        <div className="grid md:grid-cols-3 gap-12 md:gap-8">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: index * 0.15 }}
                className="relative flex md:flex-col items-start md:items-center text-left md:text-center gap-6 md:gap-4"
              >
                {/* Step circle */}
                <div className="relative z-10 flex-shrink-0">
                  <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-700 flex items-center justify-center shadow-lg">
                    <Icon className="w-7 h-7 text-blue-400" />
                  </div>
                  <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                    {step.number}
                  </span>
                </div>

                {/* Content */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-slate-400 text-sm leading-relaxed max-w-xs mx-auto">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
