const guide = "https://nisar-docs.asf.alaska.edu/products-overview/";
const sar = "https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar";
const terms = {
  retrodispersion: ["Retrodispersión", "Parte del pulso radar que vuelve al satélite. Depende de la rugosidad, la humedad y la estructura de la superficie.", sar],
  hh: ["HH", "El radar transmite y recibe en horizontal. Es sensible a la superficie, al agua y, en ciertos casos, al doble rebote.", sar],
  hv: ["HV", "El radar transmite en horizontal y recibe en vertical. La dispersión en ramas y hojas puede intensificar este canal.", sar],
  bands: ["Bandas L y C", "La banda L de NISAR y SAOCOM tiene una longitud de onda de unos 24 cm. La banda C de RADARSAT ronda los 5–6 cm. En vegetación, la penetración también depende de la humedad, la estructura y el ángulo.", sar],
  water: ["Rebote simple y doble", "El agua tranquila suele verse oscura porque desvía el pulso. El agua junto a troncos o paredes puede verse brillante por doble rebote. El viento y la geometría cambian esta respuesta.", sar],
  active: ["Sensores activos y pasivos", "El radar emite su propia señal. Una cámara óptica de luz visible registra luz reflejada. La resolución espacial indica el detalle que puede distinguirse, y la temporal, la frecuencia de observación.", "https://www.earthdata.nasa.gov/learn/earth-observation-data-basics"],
  provisional: ["Dato provisional", "ASF indica que los productos de nivel 0 a 2 provisionales están calibrados y parcialmente validados. SME2 tiene advertencias propias. Compara observaciones con la misma madurez cuando sea posible.", `${guide}#nisar-maturity-levels`],
  gcov: ["GCOV", "Potencia de retrodispersión geocodificada y corregida por terreno. GAIA compara HH y HV de observaciones compatibles.", guide],
  gunw: ["GUNW", "Interferograma geocodificado con fase desenvuelta y coherencia. Puede estimar el movimiento en la línea de visión del radar.", guide],
  sme2: ["SME2", "Estimación de humedad superficial a partir de NISAR. Es un indicador de condiciones del suelo. No mide la temperatura del aire.", guide],
} as const;

export const sensorBasicsLink = { name: "Sensores activos y pasivos · NASA Earthdata", href: terms.active[2] };

export function RadarGlossary({ terms: visible = ["retrodispersion", "hh", "hv", "bands", "water", "active"], showLinks = true }: {
  terms?: (keyof typeof terms)[]; showLinks?: boolean;
}) {
  return <div className="radar-glossary" aria-label="Glosario de radar">
    {visible.map(id => {
      const [label, description, href] = terms[id];
      return <details key={id}><summary><span aria-hidden="true">?</span> {label}</summary>
        <p>{description}</p>
        {showLinks && <a className="source-link" href={href} target="_blank" rel="noopener noreferrer">Consultar la fuente ↗</a>}
      </details>;
    })}
  </div>;
}

export function vertexGranule(name: string) {
  const url = new URL("https://search.asf.alaska.edu/");
  url.searchParams.set("dataset", "NISAR");
  url.searchParams.set("searchList", name.replace(/\.h5$/i, ""));
  url.searchParams.set("searchType", "List Search");
  return url.href;
}
