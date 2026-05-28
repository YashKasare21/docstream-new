import Link from "next/link";
import { FileQuestion, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4">
      <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center">
        <FileQuestion className="w-7 h-7 text-slate-400" />
      </div>

      <div className="text-center space-y-2 max-w-xs">
        <p className="text-slate-600 text-xs font-semibold uppercase tracking-widest">
          404
        </p>
        <h1 className="text-2xl font-bold text-white">Page Not Found</h1>
        <p className="text-slate-400 text-sm">
          That page doesn&apos;t exist. It may have been moved or deleted.
        </p>
      </div>

      <Link
        href="/"
        className="inline-flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-semibold rounded-xl transition-all duration-200"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Home
      </Link>
    </div>
  );
}
