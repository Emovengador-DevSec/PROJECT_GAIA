const observationDate = new Intl.DateTimeFormat("es-PE", {
  dateStyle: "medium", timeStyle: "short", timeZone: "UTC", hourCycle: "h23",
});
const calendarDate = new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeZone: "UTC" });

export function formatDate(value?: string | null) {
  if (!value) return "Fecha sin informar";
  const date = new Date(value);
  if (!Number.isFinite(date.valueOf())) return value;
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? calendarDate.format(date) : `${observationDate.format(date)} UTC`;
}
