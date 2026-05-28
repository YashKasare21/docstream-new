"use client";

import { Cpu, Layout, ScanText } from "lucide-react";
import { motion } from "framer-motion";

const features = [
  {
    icon: Cpu,
    title: "Gemini-powered Structuring",
    description:
      "Our semantic engine understands context. It keeps math environments, citations, and document hierarchies perfectly intact during conversion.",
    iconColor: "text-indigo-400",
  },
  {
    icon: Layout,
    title: "Template-aware Rendering",
    description:
      "Output directly into Report, IEEE, or Resume formats. Docstream handles the boilerplate so you focus on the content.",
    iconColor: "text-blue-400",
  },
  {
    icon: ScanText,
    title: "Scanned PDF Support",
    description:
      "Tesseract OCR kicks in automatically for image-based PDFs. No configuration needed — it just works.",
    iconColor: "text-cyan-400",
  },
];

export default function Features() {
  return (
    <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
      {/* Section heading */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5 }}
        className="text-center mb-16"
      >
        <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
          Built for precision
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Advanced features to handle the most demanding academic layouts
        </p>
      </motion.div>

      {/* Cards grid */}
      <div className="grid md:grid-cols-3 gap-8">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -6 }}
              className="glass-card p-6 group"
            >
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4 group-hover:bg-blue-500/20 group-hover:border-blue-500/40 group-hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] transition-all duration-300">
                <Icon className={`w-6 h-6 ${feature.iconColor}`} />
              </div>
              <h3 className="text-xl font-semibold text-white mb-3 group-hover:text-blue-100 transition-colors">
                {feature.title}
              </h3>
              <p className="text-slate-400 leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
