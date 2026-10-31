"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Marks its wrapper with data-drawn the first time it scrolls into view. */
export default function DrawOnView({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const draw = () => el.setAttribute("data-drawn", "");
    if (!("IntersectionObserver" in window)) {
      draw();
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          draw();
          io.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className="draw-on-view">
      {children}
    </div>
  );
}
