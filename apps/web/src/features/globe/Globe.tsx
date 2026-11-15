import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../../lib/useMotionPreference";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type { AOI, AlertFeature, CameraMode, GlobeStatus, OrbitData } from "../../lib/api";
import { loadAyacuchoTerrain } from "./localTerrain";
import { observationMetric } from "../workspace/AlertFeed";
import { formatDate } from "../../lib/formatDate";
import { formatNumber } from "../../lib/formatNumber";
import type { CitizenReport } from "../../lib/api";
import { addNisarOrbit } from "./nisarOrbit";
import { api } from "../../lib/api";
import { climateSummary } from "../workspace/actionSummaryModel";
import { FIELD_VIEW, PhotoPopup, usePlaceEvidence, type FieldViewRequest } from "../workspace/PlaceEvidence";
import { ZoneDeck } from "./ZoneDeck";
import { fieldContours, fieldHeights, sampleFieldSurface } from "./fieldView";
import type { RealPhoto } from "../../lib/api";
import { FIRE_AGE_ALPHA, FIRE_AGE_COLORS, fireAge } from "./fireAge";

type Props = {
  aoi?: AOI; communityCenter?: [number, number]; tileUrl?: string; beforeUrl?: string; afterUrl?: string; split: number;
  reports?: CitizenReport[]; reportPicker?: (point: [number, number]) => void; reportPoint?: [number, number];
  radarBounds?: AOI["bbox"];
  contextOverlay?: { url: string; credit: string; beforeUrl?: string };
  exaggeration: number; camera?: CameraMode; alerts: AlertFeature[]; selected?: AlertFeature;
  cameraStep?: number;
  radarRevision?: number; onRadarError: (message: string) => void;
  fireCells: AlertFeature[];
  active: boolean;
  cutoff?: number;
  orbitData?: OrbitData; orbitVisible: boolean; satelliteFocus: number;
  offline?: boolean;
  realTimeLighting: boolean;
  onSelect: (alert: AlertFeature) => void; onStatus: (status: GlobeStatus) => void;
};
const REDUCED = "(prefers-reduced-motion: reduce)";
// Same vivid cause colours as the zone sheet titles.
const CAUSE_COLORS: Record<string, string> = { incendio_sequia: "#ff6b4a", erosion_huaico: "#ffc23d",
  ladera_inestable_sismo: "#c084fc", estres_hidrico_agricola: "#38bdf8", causa_por_verificar: "#9fb0bf" };
const COLORS = { quake: "#fbbf24", fire: "#ff3b3b", surface_change: "#c69aff", deformation: "#a855f7", climate_anomaly: "#38bdf8" };

/** Chaikin corner cutting: softens the staircase edges of radar-pixel polygons for display only. */
function smoothRing(ring: number[][], iterations = 2): number[][] {
  let pts = ring.slice(0, -1);
  for (let k = 0; k < iterations; k++) {
    const next: number[][] = [];
    for (let i = 0; i < pts.length; i++) {
      const [x0, y0] = pts[i];
      const [x1, y1] = pts[(i + 1) % pts.length];
      next.push([x0 * .75 + x1 * .25, y0 * .75 + y1 * .25], [x0 * .25 + x1 * .75, y0 * .25 + y1 * .75]);
    }
    pts = next;
  }
  return [...pts, pts[0]];
}

function marker(kind: string, color: string): string {
  const shapes: Record<string, string> = {
    quake: '<circle cx="20" cy="20" r="7"/><circle cx="20" cy="20" r="14" fill="none" stroke-width="2"/>',
    fire: '<path d="M21 5c3 9-1 10 3 14 2-3 3-5 3-5 8 13 2 21-7 21C9 35 7 25 13 18c0 5 3 5 3 5-2-8 4-10 5-18z"/>',
    surface_change: '<path d="m20 5 13 8v14l-13 8-13-8V13z"/>',
    deformation: '<path d="m20 4 15 16-15 16L5 20z"/>',
    climate_anomaly: '<path d="M12 26a8 8 0 1 1 15.5-3.5A6 6 0 1 1 34 28H12a6 6 0 0 1 0-12 6 6 0 0 1 6 2"/>',
  };
  return "data:image/svg+xml," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><g fill="${color}" stroke="${color}" stroke-width="1">${shapes[kind] ?? shapes.surface_change}</g></svg>`);
}

export function Globe({ aoi, communityCenter, reports, reportPicker, reportPoint, tileUrl, beforeUrl,
  afterUrl, radarBounds, contextOverlay, split, exaggeration, camera = "oblique", cameraStep, radarRevision, onRadarError,
  alerts, fireCells, active, cutoff, orbitData, orbitVisible, satelliteFocus, selected, onSelect, onStatus, offline = false,
  realTimeLighting }: Props) {
  const {data: placeEvidence} = usePlaceEvidence(selected);
  const [fieldRequest, setFieldRequest] = useState<FieldViewRequest>();
  const [zoneTag, setZoneTag] = useState<{ zone: string; climate?: { text: string; color: string } }>();
  const zoneTagEl = useRef<HTMLDivElement>(null);
  const [designStatus, setDesignStatus] = useState<"loading" | "ready" | "unavailable">();
  const [aerialLoaded, setAerialLoaded] = useState(false);
  const fieldMode = useRef(false);
  const fieldClose = useRef<HTMLButtonElement>(null);
  const fieldTrigger = useRef<HTMLElement | null>(null);
  const [openPhoto, setOpenPhoto] = useState<RealPhoto>();
  const host = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const viewer = useRef<Cesium.Viewer | null>(null);
  const selectRef = useRef(onSelect);
  const reportPickerRef = useRef(reportPicker);
  reportPickerRef.current = reportPicker;
  const statusRef = useRef(onStatus);
  const radarErrorRef = useRef(onRadarError);
  radarErrorRef.current = onRadarError;
  const lastInput = useRef(performance.now());
  const [hover, setHover] = useState<{ feature: AlertFeature; x: number; y: number }>();
  const cutoffRef = useRef(cutoff);
  const arrival = useRef(Infinity);
  const workspaceActive = useRef(active);
  workspaceActive.current = active;
  const updateVisibility = useRef<() => void>(() => undefined);
  const orbit = useRef<{ target: Cesium.Cartesian3; heading: number; pitch: number; range: number } | undefined>(undefined);
  const [orbiting, setOrbiting] = useState(false);
  const satellite = useRef<ReturnType<typeof addNisarOrbit> | undefined>(undefined);
  const stopOrbit = () => {
    const v = viewer.current;
    if (!v) return;
    v.camera.cancelFlight();
    if (orbit.current) v.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    orbit.current = undefined;
    setOrbiting(false);
    lastInput.current = performance.now();
  };
  cutoffRef.current = cutoff;
  selectRef.current = onSelect;
  statusRef.current = onStatus;

  useEffect(() => {
    if (!host.current) return;
    const token = offline ? undefined : import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined;
    if (token) Cesium.Ion.defaultAccessToken = token;
    const v = new Cesium.Viewer(host.current, {
      animation: false, timeline: false, baseLayerPicker: false, geocoder: false,
      homeButton: false, sceneModePicker: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: false, selectionIndicator: false, baseLayer: false,
      contextOptions: { webgl: { antialias: true, alpha: false } }, msaaSamples: 4,
      useBrowserRecommendedResolution: false,
    });
    viewer.current = v;
    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      v.resolutionScale = Math.min(1, (innerWidth < 720 ? 1.5 : 2) / ratio);
    };
    resize();
    window.addEventListener("resize", resize);
    v.scene.backgroundColor = Cesium.Color.fromCssColorString("#05070a");
    v.scene.globe.baseColor = Cesium.Color.fromCssColorString("#071622");
    v.scene.globe.enableLighting = true;
    v.scene.globe.depthTestAgainstTerrain = true;
    v.scene.globe.dynamicAtmosphereLighting = true;
    v.scene.globe.maximumScreenSpaceError = 1.5;
    v.scene.highDynamicRange = true;
    v.scene.postProcessStages.fxaa.enabled = true;
    v.scene.fog.enabled = true;
    v.scene.globe.tileLoadProgressEvent.addEventListener((remaining: number) => {
      host.current?.setAttribute("aria-busy", String(remaining > 0));
    });
    if (v.scene.skyAtmosphere) v.scene.skyAtmosphere.show = true;
    v.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(-105, 4, 22_000_000) });
    let terrain: GlobeStatus["terrain"] = "loading";
    let imagery = "NASA Blue Marble · respaldo local";
    let regionalImagery: string | undefined;
    const publish = () => statusRef.current({ terrain, imagery, regionalImagery });
    publish();
    const addBase = async () => {
      let nightIndex = 1;
      const local = await Cesium.SingleTileImageryProvider.fromUrl("/globe/earth-day.jpg", { credit: "NASA Blue Marble" });
      if (v.isDestroyed()) return;
      v.imageryLayers.addImageryProvider(local, 0);
      if (token) {
        try {
          const provider = await Cesium.createWorldImageryAsync({ style: Cesium.IonWorldImageryStyle.AERIAL_WITH_LABELS });
          if (v.isDestroyed()) return;
          v.imageryLayers.addImageryProvider(provider, 1);
          nightIndex = 2;
          imagery = "Cesium ion · satélite y etiquetas";
        } catch { imagery = "NASA Blue Marble · Cesium ion no disponible"; }
      } else if (!offline) {
        const provider = new Cesium.UrlTemplateImageryProvider({
          url: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
          maximumLevel: 8, credit: "NASA GIBS · Blue Marble", enablePickFeatures: false,
        });
        const gibs = v.imageryLayers.addImageryProvider(provider, 1);
        nightIndex = 2;
        provider.errorEvent.addEventListener(() => {
          if (!v.isDestroyed()) { gibs.show = false; imagery = "NASA Blue Marble · respaldo local"; publish(); }
        });
        imagery = "NASA GIBS · Blue Marble";
      }
      publish();
      if (nightIndex === 1 || !token) {
        const response = await fetch("/globe/ayacucho-landsat.json");
        if (response.ok && !v.isDestroyed()) {
          const { bbox, date } = await response.json() as { bbox: [number, number, number, number]; date: string };
          const landsat = await Cesium.SingleTileImageryProvider.fromUrl("/globe/ayacucho-landsat.jpg", {
            rectangle: Cesium.Rectangle.fromDegrees(...bbox), credit: `NASA GIBS · Landsat WELD (${date})`,
          });
          if (v.isDestroyed()) return;
          v.imageryLayers.addImageryProvider(landsat, nightIndex++);
          regionalImagery = `NASA GIBS · Landsat WELD · ${date.slice(0, 4)}`;
          publish();
        }
      }
      const night = await Cesium.SingleTileImageryProvider.fromUrl("/globe/earth-night.jpg", { credit: "NASA Black Marble 2016" });
      if (!v.isDestroyed()) {
        v.imageryLayers.add(new Cesium.ImageryLayer(night, { dayAlpha: 0, nightAlpha: 1 }), nightIndex);
      }
    };
    addBase().catch(() => {
      if (!v.isDestroyed() && v.imageryLayers.length === 0) { imagery = "No se pudo cargar la imagen satelital"; publish(); }
    });
    const localTerrain = () => loadAyacuchoTerrain().then(provider => {
      if (!v.isDestroyed()) { v.terrainProvider = provider; terrain = "regional"; publish(); }
    }).catch(() => { if (!v.isDestroyed()) { terrain = "unavailable"; publish(); } });
    // Cesium's globe shader blends day and night imagery on terrain without vertex normals.
    if (token) Cesium.createWorldTerrainAsync({ requestVertexNormals: false }).then(provider => {
      if (!v.isDestroyed()) { v.terrainProvider = provider; terrain = "ready"; publish(); }
    }).catch(localTerrain);
    else localTerrain();
    Cesium.GeoJsonDataSource.load("/globe/peru-boundaries.geojson", {
      fill: Cesium.Color.TRANSPARENT, stroke: Cesium.Color.fromCssColorString("#a8c6d8").withAlpha(.55),
      strokeWidth: 1, clampToGround: true, credit: "geoBoundaries · CC BY 4.0",
    }).then(data => {
      if (v.isDestroyed()) return;
      for (const entity of data.entities.values) {
        const ring = entity.polygon?.hierarchy?.getValue(v.clock.currentTime)?.positions as Cesium.Cartesian3[] | undefined;
        if (!ring?.length) continue;
        const level = entity.properties?.level?.getValue(v.clock.currentTime);
        entity.polygon = undefined;
        entity.polyline = new Cesium.PolylineGraphics({
          positions: [...ring, ring[0]], clampToGround: true, width: level === 2 ? 1 : 1.6,
          material: Cesium.Color.fromCssColorString("#d9eaf5").withAlpha(level === 2 ? .55 : .72),
        });
      }
      v.dataSources.add(data);
      const updateBoundaries = () => {
        const height = v.camera.positionCartographic.height;
        data.show = height < 2_800_000;
        for (const entity of data.entities.values) {
          const level = entity.properties?.level?.getValue(v.clock.currentTime);
          entity.show = level !== 2 || height < 650_000;
        }
      };
      updateBoundaries();
      v.camera.changed.addEventListener(updateBoundaries);
    }).catch(() => { /* La imagen satelital sigue disponible. */ });
    fetch("/globe/places.geojson").then(response => {
      if (!response.ok) throw new Error("Localidades no disponibles");
      return response.json() as Promise<{ features: { geometry: { coordinates: [number, number] };
        properties: { name: string } }[] }>;
    }).then(({ features }) => {
      if (v.isDestroyed()) return;
      v.creditDisplay.addStaticCredit(new Cesium.Credit('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', true));
      for (const { properties, geometry } of features) {
        const [lon, lat] = geometry.coordinates;
        const text = properties.name === "San Miguel" ? "San Miguel · La Mar" : properties.name;
        v.entities.add({
          position: Cesium.Cartesian3.fromDegrees(lon, lat),
          point: { pixelSize: 4, color: Cesium.Color.WHITE, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND },
          label: { text, font: "16px sans-serif", fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK, outlineWidth: 3, style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(8, -10), horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1_500_000),
            disableDepthTestDistance: Number.POSITIVE_INFINITY },
        });
      }
    }).catch(() => { /* La imagen satelital sigue disponible. */ });
    const clicks = new Cesium.ScreenSpaceEventHandler(v.scene.canvas);
    let lastPick = 0;
    let highlighted: Cesium.Entity | undefined;
    let oldScale: Cesium.Property | undefined;
    let oldSize: Cesium.Property | undefined;
    let oldOutline: Cesium.Property | undefined;
    let highlightedPoint: Cesium.PointPrimitive | undefined;
    let oldPointSize = 7;
    const clearHover = () => {
      if (highlighted?.billboard) highlighted.billboard.scale = oldScale;
      if (highlighted?.point) highlighted.point.pixelSize = oldSize;
      if (highlighted?.polygon) highlighted.polygon.outlineColor = oldOutline;
      if (highlightedPoint) highlightedPoint.pixelSize = oldPointSize;
      highlightedPoint = undefined;
      highlighted = undefined;
      v.scene.canvas.style.cursor = "";
      setHover(undefined);
    };
    const leave = () => clearHover();
    v.scene.canvas.addEventListener("mouseleave", leave);
    clicks.setInputAction((event: { endPosition: Cesium.Cartesian2 }) => {
      if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
      const now = performance.now();
      if (now - lastPick < 50) return;
      lastPick = now;
      const picked = v.scene.pick(event.endPosition);
      const entity = picked?.id as Cesium.Entity | undefined;
      const feature = entity?.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
      if (!feature) { if (highlighted) clearHover(); return; }
      if (highlighted !== entity) {
        clearHover();
        highlighted = entity;
        oldScale = entity?.billboard?.scale;
        oldSize = entity?.point?.pixelSize;
        oldOutline = entity?.polygon?.outlineColor;
        if (entity?.billboard) entity.billboard.scale = new Cesium.ConstantProperty(1.35);
        if (entity?.point) entity.point.pixelSize = new Cesium.ConstantProperty(12);
        if (entity?.polygon) entity.polygon.outlineColor = new Cesium.ConstantProperty(Cesium.Color.WHITE);
        if (picked?.primitive instanceof Cesium.PointPrimitive) {
          highlightedPoint = picked.primitive;
          oldPointSize = highlightedPoint!.pixelSize;
          highlightedPoint!.pixelSize = 12;
        }
      }
      v.scene.canvas.style.cursor = "pointer";
      setHover({ feature, x: Math.max(12, Math.min(event.endPosition.x + 20, v.scene.canvas.clientWidth - 332)),
        y: Math.max(12, Math.min(event.endPosition.y + 18, v.scene.canvas.clientHeight - 205)) });
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
    clicks.setInputAction((event: { position: Cesium.Cartesian2 }) => {
      if (reportPickerRef.current) {
        const ray = v.camera.getPickRay(event.position);
        const pickedPoint = ray && v.scene.globe.pick(ray, v.scene);
        if (pickedPoint) {
          const point = Cesium.Cartographic.fromCartesian(pickedPoint);
          reportPickerRef.current([Cesium.Math.toDegrees(point.longitude), Cesium.Math.toDegrees(point.latitude)]);
        }
        return;
      }
      const picked = v.scene.pick(event.position);
      const realPhoto = picked?.id?.properties?.realPhoto?.getValue(v.clock.currentTime) as RealPhoto | undefined;
      if (realPhoto) { setOpenPhoto(realPhoto); return; }
      const feature = picked?.id?.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
      if (feature) selectRef.current(feature);
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => {
      window.removeEventListener("resize", resize);
      v.scene.canvas.removeEventListener("mouseleave", leave);
      clicks.destroy(); v.destroy(); viewer.current = null;
    };
  }, [offline]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || (!reports?.length && !reportPoint)) return;
    const data = new Cesium.CustomDataSource("Reportes ciudadanos · sin verificar");
    for (const report of reports ?? []) {
      data.entities.add({ id: report.id, name: "Reporte ciudadano · sin verificar",
        position: Cesium.Cartesian3.fromDegrees(report.lon, report.lat),
        point: { pixelSize: 11, color: Cesium.Color.fromCssColorString("#62f0be"),
          outlineWidth: 2, outlineColor: Cesium.Color.BLACK, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND } });
    }
    if (reportPoint) data.entities.add({ name: "Punto del reporte",
      position: Cesium.Cartesian3.fromDegrees(...reportPoint),
      point: { pixelSize: 14, color: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND } });
    v.dataSources.add(data);
    return () => { if (!v.isDestroyed()) v.dataSources.remove(data, true); };
  }, [reports, reportPoint, offline, active]);

  useEffect(() => {
    const canvas = viewer.current?.scene.canvas;
    if (canvas) canvas.style.cursor = reportPicker ? "crosshair" : "";
    return () => { if (canvas) canvas.style.cursor = ""; };
  }, [reportPicker]);

  useEffect(() => { if (viewer.current) viewer.current.scene.verticalExaggeration = exaggeration; }, [exaggeration, offline]);
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    if (v.scene.sun) v.scene.sun.show = realTimeLighting;
    if (realTimeLighting) {
      v.scene.light = new Cesium.SunLight();
      return;
    }
    // Aim light at the study area without changing the clock used for the orbit and observations.
    const [west, south, east, north] = aoi?.bbox ?? [-66, -17, -66, -17];
    const surface = Cesium.Cartesian3.fromDegrees((west + east) / 2, (south + north) / 2);
    const towardSurface = Cesium.Cartesian3.negate(surface, surface);
    v.scene.light = new Cesium.DirectionalLight({ direction: towardSurface, intensity: 2 });
  }, [aoi, realTimeLighting, offline]);
  useEffect(() => {
    const v = viewer.current;
    if (!v || !active) return;
    v.clock.clockStep = Cesium.ClockStep.SYSTEM_CLOCK;
    v.clock.shouldAnimate = !reduceMotion;
  }, [active, reduceMotion, offline]);
  useEffect(() => {
    const v = viewer.current;
    if (!v || !active || !orbitVisible || !orbitData?.elements) return;
    const control = addNisarOrbit(v, orbitData.elements, reduceMotion);
    satellite.current = control;
    return () => { control.dispose(); satellite.current = undefined; };
  }, [active, orbitData, orbitVisible, reduceMotion, offline]);
  useEffect(() => {
    if (satelliteFocus) { stopOrbit(); satellite.current?.focus(); }
  }, [satelliteFocus]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || !active) return;
    if (communityCenter) {
      lastInput.current = performance.now();
      v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(Cesium.Cartesian3.fromDegrees(...communityCenter), 0), {
        offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-70), 24_000),
        duration: reduceMotion ? 0 : 1.8,
      });
      return;
    }
    if (!aoi) {
      arrival.current = performance.now();
      lastInput.current = performance.now() - 16_400;
      v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(-66, -17, 11_500_000),
        duration: reduceMotion ? 0 : 3.6, easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT });
      return;
    }
    const [w, s, e, n] = radarBounds ?? aoi.bbox;
    const cam = aoi.camera ?? {};
    const pad = camera === "overview" ? 6 : 0;
    const target = Cesium.Cartesian3.fromDegrees((w + e) / 2, (s + n) / 2);
    const radius = Cesium.BoundingSphere.fromPoints([
      Cesium.Cartesian3.fromDegrees(w - pad, s - pad), Cesium.Cartesian3.fromDegrees(e + pad, n + pad),
    ]).radius;
    const range = radarBounds ? Math.max(30_000, radius * 2.8) : Math.max(camera === "zone" ? 80_000 : 120_000, radius * 3.6);
    v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, radius), {
      offset: new Cesium.HeadingPitchRange(Cesium.Math.toRadians(radarBounds ? 0 : cam.heading_deg ?? 20),
        Cesium.Math.toRadians(radarBounds || camera === "zone" ? -90 : camera === "overview" ? -60 : cam.pitch_deg ?? -38), range),
      duration: window.matchMedia(REDUCED).matches ? 0 : 2.4, easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT });
  }, [aoi, communityCenter, radarBounds, camera, cameraStep, offline, active, reduceMotion]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || !active || reduceMotion) return;
    let lastFrame = performance.now();
    const interacted = () => {
      lastInput.current = performance.now();
      v.camera.cancelFlight();
      if (orbit.current) v.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
      orbit.current = undefined;
      setOrbiting(false);
    };
    const canvas = v.scene.canvas;
    const moved = () => { lastInput.current = performance.now(); };
    canvas.addEventListener("pointerdown", interacted);
    canvas.addEventListener("pointermove", moved);
    canvas.addEventListener("wheel", interacted, { passive: true });
    window.addEventListener("keydown", interacted);
    const removeFrame = v.scene.preRender.addEventListener(() => {
      const now = performance.now();
      const delta = Math.min(.1, (now - lastFrame) / 1000);
      lastFrame = now;
      if (orbit.current) {
        orbit.current.heading += delta * .07;
        const { target, heading, pitch, range } = orbit.current;
        v.camera.lookAt(target, new Cesium.HeadingPitchRange(heading, pitch, range));
      } else if (!aoi && !selected && now - lastInput.current > 20_000 && v.camera.positionCartographic.height > 4_000_000) {
        v.camera.rotate(Cesium.Cartesian3.UNIT_Z, delta * .007);
      }
    });
    return () => {
      removeFrame();
      canvas.removeEventListener("pointerdown", interacted);
      canvas.removeEventListener("pointermove", moved);
      canvas.removeEventListener("wheel", interacted);
      window.removeEventListener("keydown", interacted);
    };
  }, [active, aoi, selected, reduceMotion, offline]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || fieldRequest) return;
    const overlays: Cesium.ImageryLayer[] = [];
    const removeErrors: (() => void)[] = [];
    const sources: [string | undefined, Cesium.SplitDirection][] = beforeUrl && afterUrl
      ? [[beforeUrl, Cesium.SplitDirection.LEFT], [afterUrl, Cesium.SplitDirection.RIGHT]]
      : [[tileUrl, Cesium.SplitDirection.NONE]];
    for (const [url, direction] of sources) if (url) {
      const provider = new Cesium.UrlTemplateImageryProvider({ url, maximumLevel: 16,
        rectangle: aoi ? Cesium.Rectangle.fromDegrees(...aoi.bbox) : undefined });
      removeErrors.push(provider.errorEvent.addEventListener(() => radarErrorRef.current(
        "El servidor no pudo entregar las imágenes radar. Reintenta la carga.",
      )));
      const layer = v.imageryLayers.addImageryProvider(provider);
      layer.alpha = .9;
      layer.splitDirection = direction;
      overlays.push(layer);
    }
    return () => {
      removeErrors.forEach(remove => remove());
      if (!v.isDestroyed()) for (const layer of overlays) v.imageryLayers.remove(layer);
    };
  }, [tileUrl, beforeUrl, afterUrl, aoi, offline, fieldRequest, radarRevision]);
  useEffect(() => { if (viewer.current) viewer.current.scene.splitPosition = split / 100; }, [split, offline]);

  const contextUrl = contextOverlay?.url;
  const contextBefore = contextOverlay?.beforeUrl;
  const contextCredit = contextOverlay?.credit;
  useEffect(() => {
    const v = viewer.current;
    if (!v || !contextUrl || !aoi || fieldRequest) return;
    let cancelled = false;
    const overlays: Cesium.ImageryLayer[] = [];
    const rectangle = Cesium.Rectangle.fromDegrees(...aoi.bbox);
    const urls = contextBefore ? [contextBefore, contextUrl] : [contextUrl];
    Promise.all(urls.map(url => Cesium.SingleTileImageryProvider.fromUrl(url, {
      credit: contextCredit,
      rectangle,
    }))).then(providers => {
      if (cancelled || v.isDestroyed()) return;
      for (const [index, provider] of providers.entries()) {
        const overlay = v.imageryLayers.addImageryProvider(provider);
        overlay.alpha = contextBefore ? .95 : .8;
        if (contextBefore) overlay.splitDirection = index ? Cesium.SplitDirection.RIGHT : Cesium.SplitDirection.LEFT;
        overlays.push(overlay);
      }
    }).catch(() => { /* The case panel retains the original source link. */ });
    return () => {
      cancelled = true;
      if (!v.isDestroyed()) overlays.forEach(overlay => v.imageryLayers.remove(overlay));
    };
  }, [aoi, contextUrl, contextBefore, contextCredit, offline, fieldRequest]);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const data = new Cesium.CustomDataSource("Alertas con fuente");
    const reduce = !!reduceMotion;
    const started = performance.now();
    let frameTime = started;
    // Both ellipse axes must use exactly the same radius in a frame.
    const phase = (offset = 0, period = 2600) => (((frameTime - started + offset) % period) + period) % period / period;
    const latest = [...alerts].filter(item => item.properties.kind === "quake")
      .sort((a, b) => b.properties.date.localeCompare(a.properties.date)).slice(0, 14);
    const animated = new Set(latest.map(item => item.properties.id));
    const individualFires: Cesium.Entity[] = [];
    const columns: Cesium.Entity[] = [];
    const fireColors = FIRE_AGE_COLORS.map(color => Cesium.Color.fromCssColorString(color));
    const fireMarkers = FIRE_AGE_COLORS.map(color => marker("fire", color));
    const reference = () => cutoffRef.current ?? Date.now();
    const points = alerts.filter(item => item.properties.kind === "fire").length > 1000
      ? v.scene.primitives.add(new Cesium.PointPrimitiveCollection()) as Cesium.PointPrimitiveCollection : undefined;
    const firePoints: { point: Cesium.PointPrimitive; date: number; lon: number; lat: number }[] = [];
    for (const feature of alerts) {
      const geometry = feature.geometry;
      let coordinates: number[] | undefined;
      if (geometry.type === "Point") coordinates = geometry.coordinates as number[];
      if (geometry.type === "Polygon") coordinates = (geometry.coordinates as number[][][])?.[0]?.[0];
      if (geometry.type === "MultiPolygon") coordinates = (geometry.coordinates as number[][][][])?.[0]?.[0]?.[0];
      if (!coordinates) continue;
      const [lon, lat] = coordinates;
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
      const p = feature.properties;
      const size = p.kind === "quake" ? 16 + (p.metrics.magnitude ?? 4) * 2 : 26;
      if (geometry.type !== "Point") continue;
      if (points && p.kind === "fire") {
        const id = new Cesium.Entity({ id: p.id, properties: { alert: feature } });
        const point = points.add({ id, position: Cesium.Cartesian3.fromDegrees(lon, lat),
          pixelSize: 7, color: fireColors[fireAge(p.date, reference())],
          outlineColor: Cesium.Color.fromCssColorString("#ffd1ab"), outlineWidth: 1,
          disableDepthTestDistance: 0, show: false });
        firePoints.push({ point, date: Date.parse(p.date), lon, lat });
        continue;
      }
      const entity = data.entities.add({ id: p.id, name: p.title,
        position: Cesium.Cartesian3.fromDegrees(lon, lat), properties: { alert: feature },
        billboard: { image: marker(p.kind, p.kind === "fire" ? FIRE_AGE_COLORS[fireAge(p.date, reference())]
          : COLORS[p.kind] ?? COLORS.surface_change), width: size, height: size,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: 0 },
      });
      if (p.kind === "fire") {
        individualFires.push(entity);
        entity.billboard!.image = new Cesium.CallbackProperty(
          () => fireMarkers[fireAge(p.date, reference())], false,
        );
        if (!reduce && entity.billboard) entity.billboard.color = new Cesium.CallbackProperty(
          (_time, result) => Cesium.Color.WHITE.withAlpha(.65 + .35 * Math.sin(phase(lat * 1000) * Math.PI) ** 2, result), false,
        );
      }
      if (p.kind === "quake") {
        const radius = 14_000 + (p.metrics.magnitude ?? 4) * 9000;
        const period = Date.now() - Date.parse(p.date) < 86_400_000 ? 2000 : 3400;
        const wave = () => phase(lat * 170, period);
        entity.ellipse = new Cesium.EllipseGraphics({
          semiMajorAxis: reduce || !animated.has(p.id) ? radius : new Cesium.CallbackProperty(() => radius * (.25 + wave()), false),
          semiMinorAxis: reduce || !animated.has(p.id) ? radius : new Cesium.CallbackProperty(() => radius * (.25 + wave()), false),
          height: 0,
          material: new Cesium.ColorMaterialProperty(reduce || !animated.has(p.id)
            ? Cesium.Color.fromCssColorString(COLORS.quake).withAlpha(.12)
            : new Cesium.CallbackProperty((_time, result) => Cesium.Color.fromCssColorString(COLORS.quake).withAlpha(.24 * (1 - wave()), result), false)),
        });
      }
    }
    for (const feature of fireCells) {
      const p = feature.properties;
      const ring = (feature.geometry.coordinates as number[][][])[0];
      const height = 2500 + Math.sqrt(p.metrics.count ?? 1) * 16_000;
      const [lon, lat] = p.center!;
      // The cell's date is its newest member up to the cutoff, so the colour follows the timeline.
      const age = () => fireAge((cell.properties!.alert.getValue(v.clock.currentTime) as AlertFeature).properties.date, reference());
      const flicker = () => .62 + .33 * Math.sin(phase(lat * 1000, 1400) * Math.PI) ** 2;
      const tint = (alpha: (tier: 0 | 1 | 2) => number) => new Cesium.CallbackProperty((_time, result) => {
        const tier = age();
        return fireColors[tier].withAlpha(alpha(tier), result);
      }, false);
      const cell: Cesium.Entity = data.entities.add({
        id: p.id, name: p.title, properties: { alert: feature },
        position: Cesium.Cartesian3.fromDegrees(lon, lat, height),
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(ring.flat()), height: 0,
          extrudedHeight: height, outline: true,
          material: new Cesium.ColorMaterialProperty(tint(tier => tier === 0 && !reduce ? flicker() : FIRE_AGE_ALPHA[tier])),
          outlineColor: tint(tier => tier === 2 ? .7 : .95),
        },
        point: { pixelSize: 5 + Math.min(6, Math.log2((p.metrics.count ?? 1) + 1)),
          color: tint(() => 1), outlineColor: Cesium.Color.fromCssColorString("#fff0d8"), outlineWidth: 1 },
      });
      columns.push(cell);
    }
    const rank = new Map(data.entities.values.map((entity, index) => [entity.id, index]));
    const visibility = () => {
      data.show = !fieldMode.current;
      if (polygons) polygons.show = !fieldMode.current;
      if (points) points.show = !fieldMode.current;
      if (fieldMode.current) return;
      const close = v.camera.positionCartographic.height < 220_000;
      const until = cutoffRef.current ?? Infinity;
      const progress = reduce ? 1 : Math.max(0, Math.min(1, (frameTime - arrival.current) / 1600));
      const revealCount = Math.ceil(progress * data.entities.values.length);
      for (const entity of data.entities.values) {
        const feature = entity.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
        entity.show = !!feature && Date.parse(feature.properties.date) <= until && rank.get(entity.id)! < revealCount;
      }
      individualFires.forEach(entity => { entity.show = entity.show && close; });
      for (const [index, { point, date, lon, lat }] of firePoints.entries()) {
        point.show = close && date <= until && index < Math.ceil(progress * firePoints.length);
        if (point.show) {
          const tier = fireAge(new Date(date).toISOString(), reference());
          point.color = fireColors[tier].withAlpha(FIRE_AGE_ALPHA[tier]);
          const terrainHeight = v.scene.globe.getHeight(Cesium.Cartographic.fromDegrees(lon, lat)) ?? 0;
          point.position = Cesium.Cartesian3.fromDegrees(lon, lat, Math.max(0, terrainHeight) * v.scene.verticalExaggeration + 10);
        }
      }
      for (const entity of columns) {
        const original = fireCells.find(cell => cell.properties.id === entity.id)!;
        const members = original.properties.members!.filter(member => Date.parse(member.date) <= until);
        entity.show = !close && members.length > 0 && rank.get(entity.id)! < revealCount;
        const current = entity.properties!.alert.getValue(v.clock.currentTime) as AlertFeature;
        if (current.properties.metrics.count !== members.length && members.length) {
          const height = 2500 + Math.sqrt(members.length) * 16_000;
          const [lon, lat] = original.properties.center!;
          entity.polygon!.extrudedHeight = new Cesium.ConstantProperty(height);
          entity.position = new Cesium.ConstantPositionProperty(Cesium.Cartesian3.fromDegrees(lon, lat, height));
          entity.properties!.alert = new Cesium.ConstantProperty({ ...original, properties: {
            ...original.properties, title: `${members.length} focos térmicos en una celda de 10 km`,
            date: members.reduce((last, member) => member.date > last ? member.date : last, ""),
            metrics: { ...original.properties.metrics, count: members.length },
          } });
        }
      }
      if (polygons) for (const entity of polygons.entities.values) {
        const feature = entity.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
        entity.show = !!feature && Date.parse(feature.properties.date) <= until && progress >= .8;
      }
    };
    const primary = alerts.filter(item => item.geometry.type !== "Point");
    let polygons: Cesium.GeoJsonDataSource | undefined;
    visibility();
    let lastProgress = -1;
    const removeClock = v.clock.onTick.addEventListener(() => {
      frameTime = performance.now();
      const progress = (frameTime - arrival.current) / 1600;
      if (!reduce && workspaceActive.current && (progress < 1 || lastProgress < 1)) {
        visibility();
        lastProgress = progress;
      }
    });
    updateVisibility.current = visibility;
    const removeCamera = v.camera.changed.addEventListener(visibility);
    const removeTerrain = v.scene.globe.tileLoadProgressEvent.addEventListener((pending: number) => {
      if (!pending) visibility();
    });
    let lastFlicker = 0;
    const removeFlicker = v.scene.preRender.addEventListener(() => {
      if (reduce || !points || v.camera.positionCartographic.height >= 220_000 || performance.now() - lastFlicker < 250) return;
      lastFlicker = performance.now();
      for (const { point, date, lat } of firePoints) if (point.show) {
        const tier = fireAge(new Date(date).toISOString(), reference());
        point.color = fireColors[tier].withAlpha(tier === 0 ? .7 + .3 * Math.sin(phase(lat * 1000) * Math.PI) ** 2 : FIRE_AGE_ALPHA[tier]);
      }
    });
    v.dataSources.add(data);
    let cancelled = false;
    if (primary.length) Cesium.GeoJsonDataSource.load({
      type: "FeatureCollection", features: primary.map(item => ({ ...item, id: item.properties.id,
        // Display only: soften the staircase edges of radar-pixel polygons (areas stay the published ones).
        geometry: item.geometry?.type === "Polygon"
          ? { ...item.geometry, coordinates: (item.geometry.coordinates as number[][][]).map(ring => smoothRing(ring)) }
          : item.geometry })),
    }, { clampToGround: true, fill: Cesium.Color.fromCssColorString(COLORS.surface_change).withAlpha(.22),
      stroke: Cesium.Color.fromCssColorString(COLORS.surface_change), strokeWidth: 3 }).then(source => {
      if (cancelled || v.isDestroyed()) return;
      polygons = source;
      for (const entity of source.entities.values) {
        const feature = primary.find(item => item.properties.id === entity.id);
        entity.properties = new Cesium.PropertyBag({ alert: feature });
        const colorHex = CAUSE_COLORS[feature?.properties.remediation?.risk_id ?? ""] ?? feature?.properties.remediation?.color_hex ?? COLORS.surface_change;
        if (entity.polygon) {
          entity.polygon.outlineColor = new Cesium.ConstantProperty(Cesium.Color.fromCssColorString(colorHex));
          if (!reduce) {
            entity.polygon.material = new Cesium.ColorMaterialProperty(
              new Cesium.CallbackProperty((_time, result) => Cesium.Color.fromCssColorString(colorHex).withAlpha(.24 + .08 * Math.sin(phase() * Math.PI), result), false),
            );
          } else {
            entity.polygon.material = new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString(colorHex).withAlpha(.28));
          }
        }
      }
      v.dataSources.add(source);
      visibility();
    }).catch(() => { /* The observation stays available in its source record. */ });
    return () => {
      cancelled = true;
      removeCamera();
      removeTerrain();
      removeClock();
      removeFlicker();
      updateVisibility.current = () => undefined;
      if (!v.isDestroyed()) {
        if (points) v.scene.primitives.remove(points);
        v.dataSources.remove(data, true);
        if (polygons) v.dataSources.remove(polygons, true);
      }
    };
  }, [alerts, fireCells, offline, reduceMotion]);

  useEffect(() => { updateVisibility.current(); setHover(undefined); }, [cutoff]);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    orbit.current = undefined;
    setOrbiting(false);
    v.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    if (!selected?.geometry || !active) return;
    const positions: number[][] = [];
    const collect = (coordinates: unknown) => {
      if (!Array.isArray(coordinates)) return;
      if (typeof coordinates[0] === "number" && typeof coordinates[1] === "number") positions.push(coordinates);
      else coordinates.forEach(collect);
    };
    collect(selected.geometry.coordinates);
    if (!positions.length) return;
    const lon = positions.reduce((sum, point) => sum + point[0], 0) / positions.length;
    const lat = positions.reduce((sum, point) => sum + point[1], 0) / positions.length;
    const elevation = v.scene.globe.getHeight(Cesium.Cartographic.fromDegrees(lon, lat)) ?? 0;
    // globe.getHeight already returns the exaggerated surface height; do not scale it twice.
    const target = Cesium.Cartesian3.fromDegrees(lon, lat, Math.max(0, elevation));
    const radius = Cesium.BoundingSphere.fromPoints(positions.map(point => Cesium.Cartesian3.fromDegrees(point[0], point[1]))).radius;
    // Small NISAR zones (a few ha) need a close, low camera so the slope and the outline are readable.
    const zone = selected.properties.kind === "surface_change" && !!selected.properties.remediation;
    const range = selected.properties.kind === "quake" ? 260_000
      : zone ? Math.min(9_000, Math.max(3_200, radius * 9)) : Math.max(65_000, radius * 3.2);
    const heading = Cesium.Math.toRadians(-25);
    const pitch = Cesium.Math.toRadians(zone ? -24 : -38);
    let cancelled = false;
    // Bright outline of the studied zone at the real (exaggerated) terrain height, plus a label.
    // Ground-clamped primitives drift with verticalExaggeration, so heights are sampled and scaled here.
    const outline: Cesium.Entity[] = [];
    let removeFollow: (() => void) | undefined;
    setZoneTag(undefined);
    if (zone) {
      const rings: number[][][] = selected.geometry.type === "Polygon" ? [(selected.geometry.coordinates as number[][][])[0]]
        : (selected.geometry.coordinates as number[][][][]).map(poly => poly[0]);
      const tone = Cesium.Color.fromCssColorString("#facc15");
      const place = selected.properties.remediation?.nearby_places?.[0];
      const lift = (c: Cesium.Cartographic) => (Number.isFinite(c.height)
        ? c.height * v.scene.verticalExaggeration : v.scene.globe.getHeight(c) ?? elevation) + 8;
      const cartos = rings.map(ring => smoothRing(ring).map(([x, y]) => Cesium.Cartographic.fromDegrees(x, y)));
      const center = Cesium.Cartographic.fromDegrees(lon, lat);
      sampleFieldSurface(v.terrainProvider, [...cartos.flat(), center]).then(() => {
          if (cancelled || v.isDestroyed()) return;
          for (const ring of cartos) {
            const pts = ring.map(c => Cesium.Cartesian3.fromRadians(c.longitude, c.latitude, lift(c)));
            outline.push(v.entities.add({ polyline: { positions: pts, width: 3, arcType: Cesium.ArcType.NONE,
              material: new Cesium.PolylineOutlineMaterialProperty({ color: tone, outlineColor: Cesium.Color.BLACK.withAlpha(.6), outlineWidth: 1 }) } }));
            outline.push(v.entities.add({ polygon: { hierarchy: pts, perPositionHeight: true,
              material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(
                () => tone.withAlpha(fieldMode.current ? 0 : .12), false,
              )) } }));
          }
          // Crisp HTML tag that follows the zone on screen (WebGL labels look blurry).
          const anchor = Cesium.Cartesian3.fromRadians(center.longitude, center.latitude, lift(center) + 20);
          setZoneTag(tag => ({ ...tag, zone: `Zona ${selected.properties.id.slice(-3)}${place ? ` · ${place.name}` : ""}` }));
          const follow = () => {
            const el = zoneTagEl.current;
            if (!el) return;
            const pos = Cesium.SceneTransforms.worldToWindowCoordinates(v.scene, anchor);
            el.style.display = pos && !fieldMode.current ? "" : "none";
            if (pos) el.style.transform = `translate(${Math.round(pos.x)}px, ${Math.round(pos.y)}px) translate(-50%, calc(-100% - 10px))`;
          };
          removeFollow = v.scene.postRender.addEventListener(follow);
        });
      const aoiId = selected.properties.aoi_id;
      if (aoiId) api.climate(aoiId).then(climate => {
        const text = climateSummary(climate);
        if (cancelled || v.isDestroyed() || !climate?.anomalies?.length || /^Sin anomal|sin publicar|desactualizado|sin evaluar/i.test(text)) return;
        const kind = /helada/i.test(text) ? "#38bdf8" : /calor/i.test(text) ? "#ff6b4a" : "#818cf8";
        setZoneTag(tag => ({ zone: tag?.zone ?? "", climate: { color: kind,
          text: `${/helada/i.test(text) ? "❄ " : "▲ "}${text.replace(/(\d+)\.(\d)/g, "$1,$2")}` } }));
      }).catch(() => undefined);
    }
    const fly = (aim: Cesium.Cartesian3) => v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(aim, 0), {
      offset: new Cesium.HeadingPitchRange(heading, pitch, range), duration: reduceMotion ? 0 : 2.6,
      easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT,
      complete: () => {
        if (!cancelled && !reduceMotion && !fieldMode.current) { orbit.current = { target: aim, heading, pitch, range }; setOrbiting(true); }
      },
    });
    // Before the terrain tiles load, getHeight is undefined and the aim falls inside the mountain.
    // For close zone views, sample the real height first (raw metres × exaggeration).
    if (zone) {
      const spot = Cesium.Cartographic.fromDegrees(lon, lat);
      sampleFieldSurface(v.terrainProvider, [spot]).then(() => {
        if (cancelled || v.isDestroyed() || fieldMode.current) return;
        fly(Number.isFinite(spot.height) ? Cesium.Cartesian3.fromDegrees(lon, lat, spot.height * v.scene.verticalExaggeration) : target);
      });
    } else fly(target);
    return () => {
      cancelled = true;
      removeFollow?.();
      setZoneTag(undefined);
      if (!v.isDestroyed()) {
        outline.forEach(entity => v.entities.remove(entity));
        v.camera.cancelFlight();
        if (orbit.current) v.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
      }
      orbit.current = undefined;
    };
  }, [selected, offline, active, reduceMotion]);

  useEffect(() => {
    const onFieldView = (event: Event) => {
      const request = (event as CustomEvent<FieldViewRequest>).detail;
      if (!active || request.zoneId !== selected?.properties.remediation?.alert_id) return;
      if (document.activeElement instanceof HTMLElement) fieldTrigger.current = document.activeElement;
      fieldMode.current = true;
      stopOrbit();
      updateVisibility.current();
      setFieldRequest(request);
    };
    window.addEventListener(FIELD_VIEW, onFieldView);
    return () => {
      window.removeEventListener(FIELD_VIEW, onFieldView);
      fieldMode.current = false;
      updateVisibility.current();
      setFieldRequest(undefined);
    };
  }, [selected, active]);

  useEffect(() => {
    const v = viewer.current;
    const geometry = selected?.geometry;
    if (!v || !active || !fieldRequest || !geometry ||
        fieldRequest.zoneId !== selected.properties.remediation?.alert_id) return;
    const plots = geometry.type === "Polygon" ? [geometry.coordinates as [number, number][][]]
      : geometry.type === "MultiPolygon" ? geometry.coordinates as [number, number][][][] : [];
    if (!plots.length) return;
    const points = plots.flatMap(plot => plot[0].map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(lon, lat)));
    const sphere = Cesium.BoundingSphere.fromPoints(points);
    const center = Cesium.Cartographic.fromCartesian(sphere.center);
    const terrain = v.terrainProvider;
    const fieldAoi = selected.properties.aoi_id;
    let cancelled = false;
    const entities: Cesium.Entity[] = [];
    const imageryLayers: Cesium.ImageryLayer[] = [];
    const aerial = placeEvidence?.field_aerial;
    setAerialLoaded(false);
    if (aerial) {
      const padding = Math.max(1_500, sphere.radius * 5) / 6_370_000;
      const around = new Cesium.Rectangle(center.longitude - padding, center.latitude - padding,
        center.longitude + padding, center.latitude + padding);
      for (const tile of aerial.tiles) {
        const rectangle = Cesium.Rectangle.fromDegrees(...tile.bounds);
        if (!Cesium.Rectangle.intersection(around, rectangle)) continue;
        Cesium.SingleTileImageryProvider.fromUrl(api.localPhoto(tile.image_url),
          {rectangle, credit: `Contains modified Copernicus Sentinel data ${aerial.date.slice(0, 4)}`})
          .then(provider => {
            if (cancelled || v.isDestroyed()) return;
            imageryLayers.push(v.imageryLayers.addImageryProvider(provider));
            setAerialLoaded(true);
            v.scene.requestRender();
          }).catch(() => undefined);
      }
    }
    const flyDown = async () => {
      await sampleFieldSurface(terrain, [center]);
      if (!Number.isFinite(center.height) && fieldAoi) {
        const [localHeight] = await fieldHeights(fieldAoi, [[Cesium.Math.toDegrees(center.longitude), Cesium.Math.toDegrees(center.latitude)]])
          .catch(() => [NaN]);
        center.height = localHeight;
      }
      if (cancelled || v.isDestroyed()) return;
      const height = Number.isFinite(center.height)
        ? center.height * v.scene.verticalExaggeration : v.scene.globe.getHeight(center) ?? 0;
      const target = Cesium.Cartesian3.fromRadians(center.longitude, center.latitude, height);
      v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, 0), {
        offset: new Cesium.HeadingPitchRange(0, -Math.PI / 2, Math.max(aerial ? 900 : 750, sphere.radius * 4)),
        duration: reduceMotion ? 0 : 1.35,
      });
    };
    void flyDown();
    if (fieldRequest.design && fieldAoi) {
      setDesignStatus("loading");
      fieldContours(fieldAoi, plots, v.scene.verticalExaggeration).then(lines => {
        if (cancelled || v.isDestroyed()) return;
        for (const positions of lines) {
          entities.push(v.entities.add({polyline: {positions, width: 3, arcType: Cesium.ArcType.NONE,
            material: Cesium.Color.fromCssColorString("#5dffcf"), depthFailMaterial: Cesium.Color.fromCssColorString("#5dffcf")}}));
        }
        setDesignStatus(lines.length ? "ready" : "unavailable");
        v.scene.requestRender();
      }).catch(() => {if (!cancelled) setDesignStatus("unavailable");});
    }
    return () => {
      cancelled = true;
      if (!v.isDestroyed()) {
        entities.forEach(entity => v.entities.remove(entity));
        imageryLayers.forEach(layer => v.imageryLayers.remove(layer));
      }
    };
  }, [fieldRequest, selected, active, reduceMotion, placeEvidence?.field_aerial]);

  useEffect(() => {
    if (fieldRequest && window.matchMedia("(max-width: 720px)").matches) fieldClose.current?.focus();
  }, [fieldRequest]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || !fieldRequest || !active) return;
    const entities = (placeEvidence?.nearby_settlements ?? []).map(place => v.entities.add({
      position: Cesium.Cartesian3.fromDegrees(...place.center),
      label: {text: place.name, font: "600 13px sans-serif", showBackground: true,
        fillColor: Cesium.Color.WHITE, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY},
    }));
    v.scene.requestRender();
    return () => {if (!v.isDestroyed()) entities.forEach(entity => v.entities.remove(entity));};
  }, [fieldRequest, placeEvidence, active]);

  useEffect(() => {
    setOpenPhoto(undefined);
    const v = viewer.current;
    if (!v || !active || !placeEvidence?.pins.length) return;
    const entities = placeEvidence.pins.map(photo => v.entities.add({
      id: `real-photo-${photo.id}`, name: photo.title,
      position: Cesium.Cartesian3.fromDegrees(photo.lon!, photo.lat!), properties: {realPhoto: photo},
      billboard: {image: api.localPhoto(photo.thumbnail_url), width: 40, height: 40,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        pixelOffset: new Cesium.Cartesian2(0, -8),
        scaleByDistance: new Cesium.NearFarScalar(1000, 1, 100000, .6)},
    }));
    return () => {if (!v.isDestroyed()) entities.forEach(entity => v.entities.remove(entity));};
  }, [placeEvidence, active, offline]);

  const metric = hover && observationMetric(hover.feature);
  return <>
    <div ref={host} className="globe" aria-label="Globo satelital de Sudamérica con observaciones georreferenciadas" />
    {zoneTag?.zone && <div ref={zoneTagEl} className="zone-tag" aria-hidden="true">
      {zoneTag.climate && <span className="zone-tag-climate" style={{ color: zoneTag.climate.color }}>{zoneTag.climate.text}</span>}
      <span className="zone-tag-name">{zoneTag.zone}</span>
    </div>}
    {fieldRequest && <aside className="field-view-caption" aria-live="polite">
      <strong>{fieldRequest.design ? "Diseño propuesto sobre el terreno" : "Mirada satelital de la zona"}</strong>
      <small>{aerialLoaded && placeEvidence?.field_aerial
        ? `${placeEvidence.field_aerial.source} · ${placeEvidence.field_aerial.date} · ${placeEvidence.field_aerial.resolution_m} m`
        : "Imagen del globo · fecha variable según proveedor"}</small>
      {fieldRequest.design && <small>{({
        loading: "Consultando elevaciones reales…",
        ready: "Líneas orientativas cada 25 m de desnivel. Requieren revisión en campo.",
        unavailable: "Sin relieve suficiente o curvas dentro de esta mancha.",
      }[designStatus ?? "loading"])}</small>}
      {fieldRequest.design && designStatus === "ready" && <small>
        <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener noreferrer">Relieve Mapzen · rejilla de ~30 m</a>
      </small>}
      <button ref={fieldClose} type="button" className="secondary-action" onClick={() => {
        fieldMode.current = false;
        stopOrbit();
        updateVisibility.current();
        setFieldRequest(undefined);
        viewer.current?.scene.requestRender();
        requestAnimationFrame(() => fieldTrigger.current?.focus());
      }}>Cerrar vista</button>
    </aside>}
    {placeEvidence && selected?.properties.remediation && <ZoneDeck data={placeEvidence} feature={selected}
      zoneId={selected.properties.remediation.alert_id} fieldOn={!!fieldRequest} onShowPins={() => {
        const v = viewer.current;
        if (!v || !placeEvidence.pins.length) return;
        stopOrbit();
        const positions = placeEvidence.pins.map(photo => Cesium.Cartesian3.fromDegrees(photo.lon!, photo.lat!));
        const sphere = Cesium.BoundingSphere.fromPoints(positions);
        v.camera.flyToBoundingSphere(sphere, {offset: new Cesium.HeadingPitchRange(0, -Math.PI / 2, Math.max(20_000, sphere.radius * 3)), duration: reduceMotion ? 0 : 1.4});
      }} />}
    {openPhoto && <PhotoPopup photo={openPhoto} onClose={() => { setOpenPhoto(undefined); document.querySelector<HTMLElement>(".zone-deck button")?.focus(); }} />}
    {orbiting && <button type="button" className="camera-tour" onClick={stopOrbit}>Detener recorrido <kbd>Esc</kbd></button>}
    {hover && metric && <div className="map-tooltip" role="tooltip" data-kind={hover.feature.properties.kind}
      data-observation={hover.feature.properties.id}
      style={{ left: hover.x, top: hover.y }}>
      <small>{hover.feature.properties.source} · {hover.feature.properties.source_kind === "primary" ? "NISAR" : "complementario"}</small>
      <strong>{hover.feature.properties.title}</strong>
      <span>{hover.feature.properties.place}</span>
      <b>{metric.value == null ? "Cifra sin publicar" : formatNumber(metric.value, metric.decimals)} <small>{metric.unit}</small></b>
      <time dateTime={hover.feature.properties.date}>{formatDate(hover.feature.properties.date)}</time>
    </div>}
  </>;
}
