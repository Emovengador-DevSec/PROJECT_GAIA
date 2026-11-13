import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

export function CountUp({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const element = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  const reduce = useReducedMotion();
  const format = new Intl.NumberFormat("es-PE", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    if (reduce) {
      node.textContent = format.format(value);
      previous.current = value;
      return;
    }
    const control = animate(previous.current, value, {
      duration: .65, ease: "easeOut",
      onUpdate: current => { node.textContent = format.format(current); previous.current = current; },
    });
    return () => control.stop();
  }, [value, decimals, reduce]);
  return <span ref={element}>{format.format(value)}</span>;
}
