import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";
const snapshot = () => window.matchMedia(QUERY).matches;
const subscribe = (notify: () => void) => {
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", notify);
  return () => media.removeEventListener("change", notify);
};

/** Also responds when the operating-system preference changes in an open session. */
export function useReducedMotion() {
  return useSyncExternalStore(subscribe, snapshot, () => true);
}
