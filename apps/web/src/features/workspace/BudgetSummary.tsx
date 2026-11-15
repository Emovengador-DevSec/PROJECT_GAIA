import type { RemediationBudget } from "../../lib/api";

const months = (timing?: string | null) => timing?.match(/\(([^)]+)\)/)?.[1] ?? timing ?? "";

/** One card per natural technique; only verified costs show a number. */
export function BudgetSummary({ items }: { items: RemediationBudget[] }) {
  return <section className="future-block budget-summary" data-tone="heal"><h4>Técnicas y presupuesto</h4>
    {items.length ? <ul className="future-cards">{items.map(item => {
      const verified = item.status === "verificado" && !!item.source && !!item.retrieved_date
        && item.cost_total_soles != null && !/por[_ ]verificar/i.test(item.source);
      return <li key={item.intervention_id} data-tone="heal">
        <div><strong>{item.name}</strong><span data-verified={verified || undefined}>{verified ? item.cost_label : "Costo por confirmar"}</span></div>
        <ul>
          {item.timing && <li>Cuándo: {months(item.timing)}</li>}
          <li>Se mide en: {item.unit.replace(/^S\/ por /, "")}</li>
          {verified && <li>Fuente: {item.source} · {item.retrieved_date}</li>}
          {verified && item.minka_discount_pct != null && <li>Con minka: −{item.minka_discount_pct} %</li>}
        </ul>
      </li>;
    })}</ul> : <p>Sin técnicas para esta mancha hasta confirmar la causa.</p>}
  </section>;
}

