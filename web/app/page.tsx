import Hero from "./components/landing/Hero";
import HowItWorks from "./components/landing/HowItWorks";
import Limitations from "./components/landing/Limitations";
import LivePreview from "./components/landing/LivePreview";
import Problem from "./components/landing/Problem";
import Science from "./components/landing/Science";
import Story from "./components/landing/Story";

export default function Home() {
  return (
    <main id="main" className="flex-1">
      <Hero />
      <Story />
      <Problem />
      <HowItWorks />
      <LivePreview />
      <Science />
      <Limitations />
    </main>
  );
}
