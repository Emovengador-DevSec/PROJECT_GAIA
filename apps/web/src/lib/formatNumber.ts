const formats = [0, 1, 2].map(maximumFractionDigits =>
  new Intl.NumberFormat("es-PE", { maximumFractionDigits, useGrouping: false }),
);

export function formatNumber(value?: number | null, decimals = 2) {
  if (value == null || !Number.isFinite(value)) return "Sin dato";
  return formats[decimals].formatToParts(value).map(part => part.type === "decimal" ? "," : part.value).join("");
}
