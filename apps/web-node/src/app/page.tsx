import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import UploadDemo from "@/components/landing/UploadDemo";
import Features from "@/components/landing/Features";
import HowItWorks from "@/components/landing/HowItWorks";
import OpenSource from "@/components/landing/OpenSource";
import Footer from "@/components/landing/Footer";

export default function Home() {
  return (
    <div className="min-h-screen text-slate-200">
      <Navbar />
      <main>
        <Hero />
        <UploadDemo />
        <div className="section-surface">
          <Features />
        </div>
        <div className="section-surface">
          <HowItWorks />
        </div>
        <OpenSource />
      </main>
      <Footer />
    </div>
  );
}
