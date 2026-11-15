import type { RemediationBudget } from "../../lib/api";

export function BudgetSummary({ items }: { items: RemediationBudget[] }) {
  return <section className="budget-summary"><h4>Presupuesto de intervención</h4>
    {items.length ? <ul>{items.map(item => {
      const verified = item.status === "verificado" && !!item.source && !!item.retrieved_date
        && item.cost_total_soles != null && !/por[_ ]verificar/i.test(item.source);
      return <li key={item.intervention_id}><strong>{item.name}</strong> · {verified ? item.cost_label : "costo por confirmar"}
        {verified && <small> · Fuente: {item.source} · {item.retrieved_date}</small>}
        {verified && item.minka_discount_pct != null && <small> · Descuento Minka documentado: {item.minka_discount_pct} %</small>}
      </li>;
    })}</ul> : <p>Sin técnicas presupuestadas para esta mancha.</p>}
  </section>;
}
