'use client'

import { useRouter } from 'next/navigation'
import { CloudUpload, ShieldCheck, FileStack, LayoutTemplate } from 'lucide-react'
import { motion } from 'framer-motion'

export default function UploadDemo() {
  const router = useRouter()

  return (
    <section id="upload" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-24">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.6 }}
        onClick={() => router.push('/convert')}
        className="relative p-12 lg:p-16 bg-slate-900/40 rounded-[2.5rem] border-2 border-dashed border-slate-800 hover:border-blue-500/50 hover:bg-slate-900/60 transition-all duration-300 group cursor-pointer"
      >
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="w-20 h-20 rounded-2xl bg-blue-500/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 group-hover:bg-blue-500/20">
            <CloudUpload className="w-10 h-10 text-blue-500" />
          </div>

          <div>
            <h3 className="text-2xl font-semibold text-white">
              Drop your PDF here
            </h3>
            <p className="text-slate-400 mt-2">or click to start converting</p>
          </div>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-slate-500 text-sm">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" />
              Private &amp; Secure
            </span>
            <span className="flex items-center gap-1.5">
              <LayoutTemplate className="w-4 h-4" />
              3 Templates
            </span>
            <span className="flex items-center gap-1.5">
              <FileStack className="w-4 h-4" />
              OCR Enabled
            </span>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
