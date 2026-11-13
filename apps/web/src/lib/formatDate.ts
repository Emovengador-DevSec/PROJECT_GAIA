const observationDate = new Intl.DateTimeFormat("es-PE", {
  dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
});

export function formatDate(value?: string | null) {
  if (!value) return "Fecha sin informar";
  const date = new Date(value);
  return Number.isFinite(date.valueOf()) ? `${observationDate.format(date)} UTC` : value;
}
