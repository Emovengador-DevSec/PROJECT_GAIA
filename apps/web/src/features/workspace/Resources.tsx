type Resource = { name: string; href: string; description: string; status: "En uso" | "Validación" | "Para aprender" };
const groups: { title: string; entries: Resource[] }[] = [
  { title: "Datos NISAR", entries: [
    { name: "ASF Data Search Vertex", href: "https://search.asf.alaska.edu/", description: "Catálogo de observaciones y selección de fechas compatibles.", status: "En uso" },
    { name: "NISAR Data User Guide", href: "https://nisar-docs.asf.alaska.edu/", description: "Productos, capas HDF5, calidad y madurez de los datos.", status: "En uso" },
    { name: "NISAR Applications White Papers", href: "https://science.nasa.gov/mission/nisar/societal-benefits/", description: "Aplicaciones sociales del radar y contexto científico de la misión.", status: "Para aprender" },
  ] },
  { title: "Datos complementarios", entries: [
    { name: "NASA Earthdata Search", href: "https://search.earthdata.nasa.gov/", description: "Buscar imágenes ópticas, OPERA y precipitación para contrastar hipótesis.", status: "Validación" },
    { name: "NASA FIRMS", href: "https://firms.modaps.eosdis.nasa.gov/", description: "Focos de calor VIIRS. La disponibilidad depende de la conexión de la fuente.", status: "Validación" },
    { name: "USGS Earthquake Catalog", href: "https://earthquake.usgs.gov/earthquakes/search/", description: "Eventos sísmicos observados, con magnitud, hora y profundidad.", status: "En uso" },
  ] },
  { title: "Otras agencias", entries: [
    { name: "CONAE · SAOCOM", href: "https://catalogos.conae.gov.ar/", description: "Banda L sudamericana para validación cruzada. Requiere registro y datos compatibles.", status: "Validación" },
    { name: "CSA · RADARSAT Constellation", href: "https://www.asc-csa.gc.ca/eng/satellites/radarsat/", description: "Contexto en banda C para comparar la respuesta del radar.", status: "Validación" },
    { name: "CSA · RADARSAT-1", href: "https://www.asc-csa.gc.ca/eng/satellites/radarsat1/", description: "Archivo histórico, sujeto a cobertura y condiciones de acceso.", status: "Validación" },
    { name: "CSA · tutorial SAR en Python", href: "https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial", description: "Ejemplos de lectura y visualización de imágenes RADARSAT.", status: "Para aprender" },
  ] },
  { title: "Aprende", entries: [
    { name: "Introducción al SAR", href: "https://science.nasa.gov/mission/nisar/get-to-know-sar/", description: "Cómo la señal radar responde al agua, el suelo y la vegetación.", status: "Para aprender" },
    { name: "Introducción a la teledetección", href: "https://www.earthdata.nasa.gov/learn", description: "Sensores activos y pasivos para observar la Tierra.", status: "Para aprender" },
    { name: "NASA ARSET", href: "https://www.earthdata.nasa.gov/learn/trainings", description: "Formación y materiales para interpretar observaciones satelitales.", status: "Para aprender" },
    { name: "NISAR StoryMaps", href: "https://science.nasa.gov/mission/nisar/arcgis-storymaps/", description: "Historias de observación terrestre y aplicaciones de NISAR.", status: "Para aprender" },
    { name: "UAVSAR Postcards", href: "https://uavdb.jpl.nasa.gov/education/postcards.html", description: "Ejemplos de lectura de imágenes radar y composiciones polarimétricas.", status: "Para aprender" },
  ] },
];

export function Resources() {
  return <section className="challenge-resources"><h3>Fuentes del reto</h3>
    <p className="muted">Las observaciones de otras agencias se mantienen identificadas. «Validación» indica recursos pendientes de integrar o contrastar.</p>
    {groups.map(group => <details key={group.title} className="resource-group"><summary>{group.title}<span>{group.entries.length}</span></summary>
      <ul>{group.entries.map(resource => <li key={resource.name}>
        <a href={resource.href} target="_blank" rel="noopener noreferrer">{resource.name} ↗</a>
        <small>{resource.status}</small><p>{resource.description}</p>
      </li>)}</ul>
    </details>)}
  </section>;
}
