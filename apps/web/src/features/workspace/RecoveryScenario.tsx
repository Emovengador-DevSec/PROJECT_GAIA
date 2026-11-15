import type { RemediationRecoveryScenario } from "../../lib/api";
import { formatNumber } from "../../lib/formatNumber";

export function RecoveryScenario({ scenario }: { scenario: RemediationRecoveryScenario }) {
  const verified = scenario.citation_status === "verificado" && !!scenario.citation_url?.startsWith("https://")
    && !!scenario.citation && !scenario.citation.toLowerCase().includes("por verificar");
  const content = <>
    <p className="status-message">Escenario con supuestos. No es una observación ni una promesa.</p>
    <p>No hay NDVI medido para esta mancha. Las ganancias relativas son supuestos por tipo de intervención,
      no una estimación calibrada de este terreno.</p>
    {!verified && <p>Fuente pendiente de verificación. No usar estos valores para solicitar fondos o atribuir resultados.</p>}
    {verified && <ul>{(["year_3", "year_5"] as const).map((key, index) => {
      const item = scenario.projected[key];
      return item && Number.isFinite(item.gain_ndvi) ? <li key={key}>
        A {index === 0 ? 3 : 5} años: {item.gain_ndvi >= 0 ? "+" : ""}{formatNumber(item.gain_ndvi, 2)} de NDVI relativo (supuesto)
      </li> : null;
    })}</ul>}
    <p>Referencia propuesta: {scenario.citation}</p>
    {verified && <a className="source-link" href={scenario.citation_url} target="_blank" rel="noopener noreferrer">Consultar fuente</a>}
    {!!scenario.limiting_factors.length && <ul>{scenario.limiting_factors.map(item => <li key={item}>{item}</li>)}</ul>}
  </>;
  return verified ? <section className="recovery-scenario-box"><h4>Escenario de ganancia relativa</h4>{content}</section>
    : <details className="recovery-scenario-box technical-details"><summary>Ver supuestos · escenario sin fuente verificada</summary>{content}</details>;
}
