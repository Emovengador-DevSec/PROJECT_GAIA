import type { TabId } from "../../config/tabs";

const paths: Record<TabId, string> = {
  alerts: "M12 3 2.5 20h19L12 3ZM12 9v5m0 3v.1",
  cases: "M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  story: "M4 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H4V4Zm16 0h-4a3 3 0 0 0-3 3m0 14a4 4 0 0 1 4-3h3V4Z",
  changes: "M4 4h16v16H4V4Zm8 0v16M8 8l-2 4 2 4m8-8 2 4-2 4",
  series: "M4 4v16h16M7 15l4-5 4 3 5-8",
  quality: "m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7l8-4Zm-4 9 3 3 5-6",
  terrain: "m2 20 7-15 5 9 3-5 5 11H2Zm5-11 2 3 2-3",
  resources: "M7 3h8l4 4v14H5V3h2Zm7 0v5h5M8 12h8m-8 4h6",
};

export function SectionIcon({ id }: { id: TabId }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[id]} /></svg>;
}
