import { GuestHeader } from '@/components/guest/GuestHeader';
import { HeroSection } from '@/components/guest/HeroSection';
import { FeaturesGrid } from '@/components/guest/FeaturesGrid';
import { LiveSignalPreview } from '@/components/guest/LiveSignalPreview';
import { HowItWorks } from '@/components/guest/HowItWorks';
import { CTASection } from '@/components/guest/CTASection';
import { GuestFooter } from '@/components/guest/GuestFooter';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-950">
      <GuestHeader />
      <HeroSection />
      <div id="features">
        <FeaturesGrid />
      </div>
      <LiveSignalPreview />
      <div id="how-it-works">
        <HowItWorks />
      </div>
      <CTASection />
      <GuestFooter />
    </div>
  );
}

