import { animate } from "framer-motion";
import { useReducedMotion } from "../../lib/useMotionPreference";
import { useEffect, useRef } from "react";
import { formatNumber } from "../../lib/formatNumber";

export function CountUp({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const element = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  const reduce = useReducedMotion();
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    if (reduce) {
      node.textContent = formatNumber(value, decimals);
      previous.current = value;
      return;
    }
    const control = animate(previous.current, value, {
      duration: .65, ease: "easeOut",
      onUpdate: current => { node.textContent = formatNumber(current, decimals); previous.current = current; },
    });
    return () => control.stop();
  }, [value, decimals, reduce]);
  return <span ref={element}>{formatNumber(value, decimals)}</span>;
}
