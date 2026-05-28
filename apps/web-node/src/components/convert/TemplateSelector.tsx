"use client";

import { FileText, BookOpen, User, Check } from "lucide-react";
import { motion } from "framer-motion";

interface TemplateSelectorProps {
  selected: string;
  onSelect: (template: string) => void;
}

const templates = [
  {
    id: "report",
    icon: FileText,
    title: "Report",
    description: "Academic reports, theses, technical documents",
    tag: "Single column",
    popular: true,
  },
  {
    id: "ieee",
    icon: BookOpen,
    title: "IEEE",
    description: "IEEE conference and journal papers",
    tag: "Two column",
    popular: false,
  },
  {
    id: "resume",
    icon: User,
    title: "Resume",
    description: "Clean professional CV and resume format",
    tag: "Compact",
    popular: false,
  },
];

export default function TemplateSelector({
  selected,
  onSelect,
}: TemplateSelectorProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">
        Choose a template
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {templates.map((tmpl) => {
          const Icon = tmpl.icon;
          const isSelected = selected === tmpl.id;
          return (
            <motion.button
              key={tmpl.id}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelect(tmpl.id)}
              className={`relative glass-card p-5 cursor-pointer text-left transition-all duration-200 ${
                isSelected
                  ? "border-blue-500/60 bg-blue-500/[0.06] shadow-[0_0_20px_rgba(59,130,246,0.15)]"
                  : "border border-white/[0.06] hover:border-white/[0.15]"
              }`}
            >
              {/* Popular badge — top-left, green */}
              {tmpl.popular && (
                <span className="absolute top-3 left-3 text-xs px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400">
                  Popular
                </span>
              )}

              {/* Selected checkmark — top-right filled circle */}
              {isSelected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  className="absolute top-3 right-3 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center"
                >
                  <Check className="w-3 h-3 text-white" />
                </motion.div>
              )}

              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 transition-colors ${
                  isSelected ? "bg-blue-500/20" : "bg-white/[0.06]"
                } ${tmpl.popular ? "mt-6" : ""}`}
              >
                <Icon
                  className={`w-5 h-5 ${
                    isSelected ? "text-blue-400" : "text-slate-400"
                  }`}
                />
              </div>

              <h4
                className={`font-semibold mb-1 ${
                  isSelected ? "text-white" : "text-slate-200"
                }`}
              >
                {tmpl.title}
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                {tmpl.description}
              </p>
              <span className="inline-flex text-xs px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-slate-400 mt-2">
                {tmpl.tag}
              </span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
