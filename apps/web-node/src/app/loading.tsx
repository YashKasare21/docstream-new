export default function Loading() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6">
      {/* Spinning rings */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-2 border-slate-700" />
        <div className="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
      </div>

      <div className="text-center space-y-1">
        <p className="text-white font-semibold">Loading&hellip;</p>
        <p className="text-slate-500 text-sm">Hang tight</p>
      </div>
    </div>
  );
}
