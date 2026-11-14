/** Pestañas. Cada una responde a un punto del enunciado del reto (ver docs/06_Requisitos_del_Reto.md). */
export type TabId = "story" | "cases" | "changes" | "series" | "quality" | "terrain" | "alerts" | "resources" | "community";

export const TABS: { id: TabId; label: string }[] = [
  { id: "story", label: "Historia" },
  { id: "cases", label: "Lugares" },
  { id: "changes", label: "Cambios" },
  { id: "series", label: "Tiempo" },
  { id: "quality", label: "Calidad" },
  { id: "terrain", label: "Relieve 3D" },
  { id: "alerts", label: "Alertas" },
  { id: "resources", label: "Fuentes" },
  { id: "community", label: "Mi comunidad" },
];
