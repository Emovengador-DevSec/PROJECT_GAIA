import { useEffect, useState } from "react";
import "./intro.css";

/** Decorative orbital transition; it does not represent measured data. */
export function FringeIntro({ onDone }: { onDone: () => void }) {
  const [gone, setGone] = useState(false);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let completed = false;
    const finish = () => {
      if (completed) return;
      completed = true;
      setGone(true);
      onDone();
    };
    if (preference.matches) { finish(); return; }
    const onPreference = () => { if (preference.matches) finish(); };
    preference.addEventListener("change", onPreference);
    const timer = window.setTimeout(finish, 1800);
    return () => {
      window.clearTimeout(timer);
      preference.removeEventListener("change", onPreference);
    };
  }, [onDone]);
  if (gone) return null;
  return <div className="orbital-intro" aria-hidden="true">
    <div className="orbital-intro-orbits">
      <svg viewBox="0 0 1000 1000" fill="none">
        <ellipse cx="500" cy="500" rx="440" ry="175" transform="rotate(-35 500 500)" />
        <ellipse cx="500" cy="500" rx="365" ry="440" transform="rotate(-35 500 500)" />
        <path d="M500 34v22m0 888v22M34 500h22m888 0h22" />
      </svg>
    </div>
    <div className="orbital-intro-sweep"><div /></div>
  </div>;
}
