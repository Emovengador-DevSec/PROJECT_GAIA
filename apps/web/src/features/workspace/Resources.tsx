import type { AOI, AlertKind, FeedStatus, Health } from "../../lib/api";
import { formatDate } from "../../lib/formatDate";

type Link = { name: string; href: string };
type Resource = Link & { use: string; status: string; reference?: { about: string; role: string; method: string; phases: string } };

const challengeUrl = "https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/";
const earthdata = "https://www.earthdata.nasa.gov/learn/earth-observation-data-basics";
const nisar = "https://science.nasa.gov/mission/nisar";

export const nisarGuide = "https://nisar-docs.asf.alaska.edu/";
export const uavsarPostcards = "https://uavsar.jpl.nasa.gov/education/postcards.html";
export const training: Link = {
  name: "Curso SAR en español · NASA ARSET",
  href: "https://www.youtube.com/watch?v=pDQ0XTDexHA",
};

const sar: Link = { name: "Cómo funciona el radar SAR · NASA Earthdata", href: `${earthdata}/sar` };
const storymaps = `${nisar}/arcgis-storymaps/`;
const applications: Link = { name: "Aplicaciones de NISAR · NASA", href: `${nisar}/societal-benefits/` };
const fires: Link = {
  name: "Cómo se estudian los incendios · NASA StoryMaps",
  href: "https://storymaps.arcgis.com/stories/4724cd32c4064b9eb5ebe300c1385d07",
};
const subsidence: Link = {
  name: "Cómo se observa el hundimiento del terreno · NASA StoryMaps",
  href: "https://storymaps.arcgis.com/stories/109e602e748346f3be8dc89124619828",
};
const opera: Link = { name: "OPERA DIST-HLS · NASA/JPL", href: "https://doi.org/10.5067/SNWG/OPERA_L3_DIST-ALERT-HLS_V1.001" };
const gpm: Link = { name: "Precipitación GPM IMERG · NASA", href: "https://gpm.nasa.gov/data/imerg" };

const whitePapers = "https://assets.science.nasa.gov/content/dam/science/missions/nisar/nisar-jpl/pdf/";
const topics = {
  quake: { title: "Sismos", document: "Earthquake%20NISAR_WhitePaper_final.pdf", text: "El radar puede cartografiar desplazamientos después de un sismo y orientar inspecciones del terreno." },
  fire: { title: "Gestión de incendios", document: "NISAR_Applications_Fire_Management1.pdf", text: "Combinar observaciones radar con focos térmicos, imágenes ópticas y trabajo de campo ayuda a delimitar perturbaciones y seguir la recuperación." },
  volcano: { title: "Riesgo volcánico", document: "NISAR_Applications_Volcanic_Hazards.pdf", text: "Las series radar permiten detectar cambios de forma del volcán. La interpretación se contrasta con sismicidad y observaciones de campo." },
  landslide: { title: "Deslizamientos", document: "NISAR_Applications_Landslides.pdf", text: "Cartografiar movimientos y depósitos en laderas permite priorizar la inspección de poblaciones y vías." },
  forest: { title: "Perturbaciones forestales", document: "NISAR_Applications_Timber_and_Forest_Disturbance.pdf", text: "Una secuencia de observaciones permite seguir pérdidas de cobertura y estudiar su recuperación con datos independientes." },
};

/** NASA application document for this kind of observation, as a single link. */
export function applicationLink(kind?: AlertKind, aoi?: string): Link {
  const topic = kind === "quake" ? topics.quake
    : kind === "fire" || aoi === "ayacucho-huanta" ? topics.fire
    : aoi === "chosica-rimac" ? topics.landslide
    : kind === "deformation" || aoi === "sabancaya" ? topics.volcano : topics.forest;
  return { name: `${topic.title} · documento de NASA`, href: whitePapers + topic.document };
}

export function ApplicationReference({ kind, aoi }: { kind?: AlertKind; aoi?: string }) {
  const topic = kind === "quake" ? topics.quake
    : kind === "fire" || aoi === "ayacucho-huanta" ? topics.fire
    : aoi === "chosica-rimac" ? topics.landslide
    : kind === "deformation" || aoi === "sabancaya" ? topics.volcano : topics.forest;
  return <section className="alert-application">
    <h4>¿Para qué sirve esto?</h4>
    <p>{topic.text}</p>
    <div className="resource-links"><ResourceLink name={`${topic.title} · documento de NASA`} href={whitePapers + topic.document} /></div>
  </section>;
}

const alertReferences: Record<AlertKind, Link[]> = {
  quake: [applications, subsidence],
  deformation: [subsidence, applications],
  fire: [fires, opera],
  surface_change: [applications, sar],
  climate_anomaly: [gpm, applications],
};
const storyReferences: Record<string, Link[]> = {
  "ayacucho-huanta": [fires, opera],
  sabancaya: [applications, subsidence],
  "chosica-rimac": [gpm, { name: "Cómo se estudian las inundaciones · NASA StoryMaps", href: "https://storymaps.arcgis.com/stories/c00d7691b8004b20a14f28df710d05fd" }],
  "madre-de-dios-la-pampa": [opera, applications],
};
const worldviewLayers: Record<string, { id: string; name: string }> = {
  "ayacucho-huanta": { id: "OPERA_L3_DIST-ALERT-HLS_Color_Index", name: "Explorar cambios de vegetación en Ayacucho" },
  "madre-de-dios-la-pampa": { id: "OPERA_L3_DIST-ALERT-HLS_Color_Index", name: "Explorar cambios de vegetación en Madre de Dios" },
  "chosica-rimac": { id: "IMERG_Precipitation_Rate", name: "Explorar precipitación en Chosica" },
};

function worldviewLink(aoi?: AOI, date?: string): Link | undefined {
  if (!aoi) return undefined;
  const product = worldviewLayers[aoi.id];
  if (!product) return undefined;
  const [west, south, east, north] = aoi.bbox;
  const pad = (east - west) * .6;
  const map = new URL("https://worldview.earthdata.nasa.gov/");
  map.searchParams.set("l", `${product.id},MODIS_Terra_CorrectedReflectance_TrueColor`);
  map.searchParams.set("v", [west - pad, south - pad, east + pad, north + pad].join(","));
  if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) map.searchParams.set("t", `${date}T00:00:00Z`);
  return { name: `${product.name} · NASA Worldview`, href: map.href };
}

const nasaResources: Resource[] = [
  { name: "NASA Earthdata Search", href: "https://search.earthdata.nasa.gov/search", use: "Localizar las observaciones complementarias.", status: "Catálogo externo",
    reference: { about: "Buscador de datos de ciencias de la Tierra con filtros de lugar, tiempo y producto.", role: "Aporta evidencia independiente para interpretar los cambios radar.", method: "GAIA muestra OPERA para vegetación, FIRMS para focos térmicos e IMERG para la precipitación. Cada fuente conserva su propia fecha y procedencia.", phases: "F2, F3" } },
  { name: "ASF Data Search Vertex", href: "https://search.asf.alaska.edu/", use: "Seleccionar observaciones NISAR por fecha, trayectoria y marco.", status: "Catálogo en GAIA",
    reference: { about: "Interfaz de búsqueda del archivo radar ASF DAAC.", role: "Permite verificar huella, órbita, dirección y polarización antes de descargar.", method: "Calidad muestra identificadores y enlaces por gránulo. El par activo de Ayacucho comparte trayectoria 147 ascendente, marco 171, HH/HV y la misma versión de procesamiento.", phases: "F1 · G1" } },
  { name: "NISAR Data User Guide", href: nisarGuide, use: "Consultar los productos y las advertencias de calidad.", status: "Documentación técnica",
    reference: { about: "Manual de ASF para acceso, estructura HDF5, calibración y madurez.", role: "Documenta GCOV para retrodispersión, GUNW para interferometría y SME2 para humedad del suelo.", method: "GAIA enlaza la madurez desde Calidad. Los grupos internos se inspeccionan en los gránulos reales antes de procesar.", phases: "F1" } },
  { ...sar, use: "Interpretar la retrodispersión y distinguir HH y HV.", status: "Glosario integrado",
    reference: { about: "Introducción de NASA al radar de apertura sintética, polarización y tipos de rebote.", role: "Explica por qué agua tranquila, vegetación y superficies urbanas responden de manera diferente.", method: "En Historia y Cambios, el glosario explica bandas L y C, HH, HV, dispersión y doble rebote.", phases: "F4, F5" } },
  { name: "Introducción a la teledetección", href: `${earthdata}/remote-sensing`, use: "Entender qué miden una cámara óptica y un radar.", status: "Paso en la historia",
    reference: { about: "Guía de sensores activos, pasivos y resoluciones espacial, temporal y espectral.", role: "Explica la utilidad del radar ante nubosidad y la distinta cadencia de los sensores.", method: "La historia de Ayacucho explica cómo se obtienen las observaciones, el aviso térmico en horas y el ciclo orbital NISAR de 12 días.", phases: "F5" } },
  { name: "NASA ARSET Trainings", href: "https://appliedsciences.nasa.gov/get-involved/training", use: "Aprender a interpretar observaciones radar en español.", status: "Enlace en la historia",
    reference: { about: "Capacitaciones de NASA sobre teledetección y aplicaciones en agua, desastres y agricultura.", role: "Da a docentes, estudiantes y autoridades una guía para interpretar el mapa.", method: "Aprende más y el modo técnico enlazan la introducción SAR en español.", phases: "F5" } },
  { name: "NISAR StoryMaps", href: storymaps, use: "Explorar historias sobre incendios, inundaciones y hundimiento.", status: "Referencia en fichas e historias",
    reference: { about: "Relatos de NASA que combinan mapas, explicaciones y observaciones.", role: "Ayuda a comunicar cada caso con una pregunta, un cambio de cámara y su evidencia.", method: "Las fichas y relatos enlazan los ejemplos relevantes para sus fenómenos.", phases: "F5" } },
  { ...applications, name: "NISAR Applications White Papers", use: "Vincular una observación con su posible utilidad social.", status: "Documentos en fichas e historias",
    reference: { about: "Fichas técnicas breves de NASA sobre aplicaciones de NISAR.", role: "Explican usos en sismos, volcanes, deslizamientos, incendios y bosques.", method: "¿Para qué sirve esto? enlaza el documento temático y explica el beneficio en el contexto de cada caso.", phases: "F3, F5" } },
  { name: "UAVSAR Postcards", href: uavsarPostcards, use: "Interpretar composiciones radar en falso color.", status: "Referencia de la cortina",
    reference: { about: "Galería de imágenes polarimétricas del radar aerotransportado de NASA/JPL.", role: "Permite distinguir patrones visibles al combinar varios canales.", method: "La cortina usa HH en rojo, HV en verde y HH/HV en azul, con los mismos límites en ambas fechas. Los colores muestran señal radar.", phases: "F1, F4" } },
];

const partnerResources: Resource[] = [
  { name: "Catálogo SAOCOM · CONAE", href: "https://catalogos.conae.gov.ar/catalogo/catalogoSatSaocomInfo.html", use: "Buscar observaciones de banda L sobre Ayacucho.", status: "Acceso y cobertura pendientes",
    reference: { about: "Catálogo de los radares argentinos SAOCOM 1A y 1B.", role: "Permite contrastar cambios observados por dos misiones de banda L.", method: "La comparación requiere fechas, cobertura, polarización y condiciones de uso compatibles. Las hectáreas y el porcentaje se publican con las observaciones verificadas.", phases: "F3" } },
  { name: "Registro SAOCOM ONE CLICK · CONAE", href: "https://www.argentina.gob.ar/noticias/la-informacion-saocom-cada-vez-mas-accesible", use: "Consultar las condiciones de acceso al catálogo argentino.", status: "Requiere cuenta personal",
    reference: { about: "Protocolo de CONAE para registrar un perfil ONE CLICK.", role: "Habilita la búsqueda y solicitud de productos según las condiciones del programa.", method: "La persona titular registra su perfil y revisa la licencia antes de compartir o usar una escena.", phases: "F3" } },
  { name: "Datos RADARSAT Constellation · CSA", href: "https://donnees-data.asc-csa.gc.ca/en/dataset/rcm", use: "Comparar la respuesta de banda C con la banda L de NISAR.", status: "Consulta pública sin escenas en las zonas estudiadas",
    reference: { about: "Constelación canadiense de tres satélites radar de banda C.", role: "Ilustra cómo la longitud de onda influye en la respuesta a la vegetación.", method: "La búsqueda pública de EODMS no devolvió escenas RCM para las cajas de GAIA. El glosario explica las diferencias de banda.", phases: "F5" } },
  { name: "Tutorial SAR en Python · CSA", href: "https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial", use: "Buscar y revisar imágenes canadienses con Python.", status: "Referencia del recorte histórico",
    reference: { about: "Ejemplos de acceso a EODMS y visualización de datos radar canadienses.", role: "Orienta la selección por huella y la verificación de coordenadas.", method: "GAIA consulta el catálogo y verifica el sistema de referencia al reproyectar el recorte de RADARSAT-1 al globo.", phases: "F3, F5" } },
  { name: "Datos RADARSAT-1 · CSA", href: "https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1", use: "Explorar imágenes históricas de banda C.", status: "Cobertura histórica encontrada",
    reference: { about: "Archivo abierto del satélite canadiense operativo entre 1995 y 2013.", role: "Aporta una vista histórica del territorio.", method: "GAIA muestra una vista cualitativa con fecha y escena de origen. Las bandas, geometrías y épocas requieren tratamiento independiente para cualquier cálculo.", phases: "F5" } },
];

export function ResourceLink({ name, href }: Link) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{name}{" "}
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true">
      <path d="M5 11 12 4M6 4h6v6" />
    </svg>
  </a>;
}

export function LearnMore({ aoi, date, kind, onResources }: { aoi?: AOI; date?: string; kind?: AlertKind; onResources: () => void }) {
  const localReferences = kind ? alertReferences[kind] : storyReferences[aoi?.id ?? ""] ?? [];
  const map = worldviewLink(aoi, date);
  const links = kind ? localReferences : [...(map ? [map] : []), ...localReferences, sar, training];
  return <details className="technical-details learn-more">
    <summary>Aprende más</summary>
    <ul className="resource-links">{links.map(link => <li key={link.href}><ResourceLink {...link} /></li>)}</ul>
    {map && !kind && <p className="muted">En Worldview puedes elegir la fecha y revisar la cobertura de la fuente complementaria.</p>}
    <button type="button" className="text-button" onClick={onResources}>Ver todas las fuentes del reto</button>
  </details>;
}

function feedLabel(feed?: FeedStatus) {
  if (feed?.stale) return "Copia guardada";
  if (feed?.status === "ok") return "Datos disponibles";
  return "Sin datos disponibles";
}

export function Resources({ sources, health }: { sources: FeedStatus[]; health?: Health }) {
  const usgs = sources.find(source => source.source.toUpperCase().includes("USGS"));
  const firms = sources.find(source => source.source.toUpperCase().includes("FIRMS"));
  const complementary: Resource[] = [
    { name: "USGS · Sismos", href: "https://earthquake.usgs.gov/earthquakes/search/", status: feedLabel(usgs),
      use: usgs?.last_updated ? `Última consulta · ${formatDate(usgs.last_updated)}.` : "Registro de sismos observados." },
    { name: "NASA FIRMS · Focos de calor", href: "https://firms.modaps.eosdis.nasa.gov/", status: feedLabel(firms),
      use: firms?.last_updated ? `Última consulta · ${formatDate(firms.last_updated)}. ${health?.credentials.firms ? "" : "Archivo público de 24 h."}`.trim()
        : "Detecciones térmicas VIIRS para examinar actividad de fuego." },
    { ...opera, use: "Consultar perturbaciones de vegetación en Ayacucho y Madre de Dios.", status: "Capa en las historias" },
    { ...gpm, use: "Consultar la intensidad de precipitación durante el episodio de Chosica.", status: "Capa en la historia" },
  ];
  const groups = [
    { id: "nasa", title: "NASA", entries: nasaResources },
    { id: "partners", title: "Agencias socias", entries: partnerResources },
    { id: "complementary", title: "Fuentes complementarias", entries: complementary },
  ];
  return <section className="challenge-resources" aria-labelledby="challenge-resources-title">
    <p className="panel-introduction">{nasaResources.length + partnerResources.length} recursos de Dancing with the SARs y su aplicación en GAIA.</p>
    <div className="resource-links"><ResourceLink name="Consultar el reto en NASA Space Apps" href={challengeUrl} /></div>
    {groups.map(group => <details key={group.id} className="resource-group" data-source-group={group.id}>
      <summary>{group.title}<span>{group.entries.length}</span></summary>
      <ul>{group.entries.map(resource => <li key={resource.href}>
        <ResourceLink {...resource} />
        <small>{resource.status}</small>
        <p>{resource.use}</p>
        {resource.reference && <details className="resource-notes">
          <summary>Cómo se usa en GAIA</summary>
          <dl><dt>Qué es</dt><dd>{resource.reference.about}</dd>
            <dt>Qué aporta</dt><dd>{resource.reference.role}</dd>
            <dt>Uso en GAIA</dt><dd>{resource.reference.method}</dd>
            <dt>Fases del plan</dt><dd>{resource.reference.phases}</dd></dl>
        </details>}
      </li>)}</ul>
    </details>)}
  </section>;
}
