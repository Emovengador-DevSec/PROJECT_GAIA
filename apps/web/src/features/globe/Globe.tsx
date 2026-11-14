import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../../lib/useMotionPreference";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type { AOI, AlertFeature, CameraMode, GlobeStatus, OrbitData } from "../../lib/api";
import { loadAyacuchoTerrain } from "./localTerrain";
import { observationMetric } from "../workspace/AlertFeed";
import { formatDate } from "../../lib/formatDate";
import { addNisarOrbit } from "./nisarOrbit";

type Props = {
  aoi?: AOI; tileUrl?: string; beforeUrl?: string; afterUrl?: string; split: number;
  radarBounds?: AOI["bbox"];
  contextOverlay?: { url: string; credit: string; beforeUrl?: string };
  exaggeration: number; camera?: CameraMode; alerts: AlertFeature[]; selected?: AlertFeature;
  fireCells: AlertFeature[];
  active: boolean;
  cutoff?: number;
  orbitData?: OrbitData; orbitVisible: boolean; satelliteFocus: number;
  offline?: boolean;
  realTimeLighting: boolean;
  onSelect: (alert: AlertFeature) => void; onStatus: (status: GlobeStatus) => void;
};
const REDUCED = "(prefers-reduced-motion: reduce)";
const COLORS = { quake: "#fbbf24", fire: "#ff3b3b", surface_change: "#ff8a00", deformation: "#a855f7" };

function marker(kind: string, color: string): string {
  const shapes: Record<string, string> = {
    quake: '<circle cx="20" cy="20" r="7"/><circle cx="20" cy="20" r="14" fill="none" stroke-width="2"/>',
    fire: '<path d="M21 5c3 9-1 10 3 14 2-3 3-5 3-5 8 13 2 21-7 21C9 35 7 25 13 18c0 5 3 5 3 5-2-8 4-10 5-18z"/>',
    surface_change: '<path d="m20 5 13 8v14l-13 8-13-8V13z"/>',
    deformation: '<path d="m20 4 15 16-15 16L5 20z"/>',
  };
  return "data:image/svg+xml," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><g fill="${color}" stroke="${color}" stroke-width="1">${shapes[kind] ?? shapes.surface_change}</g></svg>`);
}

export function Globe({ aoi, tileUrl, beforeUrl, afterUrl, radarBounds, contextOverlay, split, exaggeration, camera = "oblique",
  alerts, fireCells, active, cutoff, orbitData, orbitVisible, satelliteFocus, selected, onSelect, onStatus, offline = false,
  realTimeLighting }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const viewer = useRef<Cesium.Viewer | null>(null);
  const selectRef = useRef(onSelect);
  const statusRef = useRef(onStatus);
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
      const picked = v.scene.pick(event.position);
      const feature = picked?.id?.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
      if (feature) selectRef.current(feature);
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => {
      window.removeEventListener("resize", resize);
      v.scene.canvas.removeEventListener("mouseleave", leave);
      clicks.destroy(); v.destroy(); viewer.current = null;
    };
  }, [offline]);

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
  }, [aoi, radarBounds, camera, offline, active, reduceMotion]);

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
        orbit.current.heading += delta * .025;
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
    if (!v) return;
    const overlays: Cesium.ImageryLayer[] = [];
    const sources: [string | undefined, Cesium.SplitDirection][] = beforeUrl && afterUrl
      ? [[beforeUrl, Cesium.SplitDirection.LEFT], [afterUrl, Cesium.SplitDirection.RIGHT]]
      : [[tileUrl, Cesium.SplitDirection.NONE]];
    for (const [url, direction] of sources) if (url) {
      const layer = v.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({ url, maximumLevel: 16,
        rectangle: aoi ? Cesium.Rectangle.fromDegrees(...aoi.bbox) : undefined }));
      layer.alpha = .9;
      layer.splitDirection = direction;
      overlays.push(layer);
    }
    return () => { if (!v.isDestroyed()) for (const layer of overlays) v.imageryLayers.remove(layer); };
  }, [tileUrl, beforeUrl, afterUrl, aoi, offline]);
  useEffect(() => { if (viewer.current) viewer.current.scene.splitPosition = split / 100; }, [split, offline]);

  const contextUrl = contextOverlay?.url;
  const contextBefore = contextOverlay?.beforeUrl;
  const contextCredit = contextOverlay?.credit;
  useEffect(() => {
    const v = viewer.current;
    if (!v || !contextUrl || !aoi) return;
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
  }, [aoi, contextUrl, contextBefore, contextCredit, offline]);

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
          pixelSize: 7, color: Cesium.Color.fromCssColorString("#ff6c3d"),
          outlineColor: Cesium.Color.fromCssColorString("#ffd1ab"), outlineWidth: 1,
          disableDepthTestDistance: 0, show: false });
        firePoints.push({ point, date: Date.parse(p.date), lon, lat });
        continue;
      }
      const entity = data.entities.add({ id: p.id, name: p.title,
        position: Cesium.Cartesian3.fromDegrees(lon, lat), properties: { alert: feature },
        billboard: { image: marker(p.kind, COLORS[p.kind] ?? COLORS.surface_change), width: size, height: size,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: 0 },
      });
      if (p.kind === "fire") {
        individualFires.push(entity);
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
      const recent = Date.now() - Date.parse(p.date) < 43_200_000;
      const color = Cesium.Color.fromCssColorString(recent ? "#ff5537" : "#ff9c43");
      const [lon, lat] = p.center!;
      const cell = data.entities.add({
        id: p.id, name: p.title, properties: { alert: feature },
        position: Cesium.Cartesian3.fromDegrees(lon, lat, height),
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(ring.flat()), height: 0,
          extrudedHeight: height, material: color.withAlpha(.72), outline: true,
          outlineColor: color.withAlpha(.95),
        },
        point: { pixelSize: 5 + Math.min(6, Math.log2((p.metrics.count ?? 1) + 1)),
          color, outlineColor: Cesium.Color.fromCssColorString("#fff0d8"), outlineWidth: 1 },
      });
      columns.push(cell);
    }
    const rank = new Map(data.entities.values.map((entity, index) => [entity.id, index]));
    const visibility = () => {
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
      for (const { point, lat } of firePoints) if (point.show) {
        point.color = Cesium.Color.fromCssColorString("#ff6c3d").withAlpha(.7 + .3 * Math.sin(phase(lat * 1000) * Math.PI) ** 2);
      }
    });
    v.dataSources.add(data);
    let cancelled = false;
    if (primary.length) Cesium.GeoJsonDataSource.load({
      type: "FeatureCollection", features: primary.map(item => ({ ...item, id: item.properties.id })),
    }, { clampToGround: true, fill: Cesium.Color.fromCssColorString("#ff8a00").withAlpha(.22),
      stroke: Cesium.Color.fromCssColorString("#ffad4f"), strokeWidth: 3 }).then(source => {
      if (cancelled || v.isDestroyed()) return;
      polygons = source;
      for (const entity of source.entities.values) {
        const feature = primary.find(item => item.properties.id === entity.id);
        entity.properties = new Cesium.PropertyBag({ alert: feature });
        if (entity.polygon && !reduce) entity.polygon.material = new Cesium.ColorMaterialProperty(
          new Cesium.CallbackProperty((_time, result) => Cesium.Color.fromCssColorString("#ff8a00").withAlpha(.18 + .08 * Math.sin(phase() * Math.PI), result), false),
        );
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
    const target = Cesium.Cartesian3.fromDegrees(lon, lat, Math.max(0, elevation) * exaggeration);
    const radius = Cesium.BoundingSphere.fromPoints(positions.map(point => Cesium.Cartesian3.fromDegrees(point[0], point[1]))).radius;
    const range = selected.properties.kind === "quake" ? 260_000 : Math.max(65_000, radius * 3.2);
    const heading = Cesium.Math.toRadians(-25);
    const pitch = Cesium.Math.toRadians(-38);
    let cancelled = false;
    v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, 0), {
      offset: new Cesium.HeadingPitchRange(heading, pitch, range), duration: reduceMotion ? 0 : 2.6,
      easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT,
      complete: () => {
        if (!cancelled && !reduceMotion) { orbit.current = { target, heading, pitch, range }; setOrbiting(true); }
      },
    });
    return () => {
      cancelled = true;
      v.camera.cancelFlight();
      if (orbit.current && !v.isDestroyed()) v.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
      orbit.current = undefined;
    };
  }, [selected, offline, active, reduceMotion]);

  const metric = hover && observationMetric(hover.feature);
  return <>
    <div ref={host} className="globe" aria-label="Globo satelital de Sudamérica con observaciones georreferenciadas" />
    {orbiting && <button type="button" className="camera-tour" onClick={stopOrbit}>Detener recorrido <kbd>Esc</kbd></button>}
    {hover && metric && <div className="map-tooltip" role="tooltip" data-kind={hover.feature.properties.kind}
      data-observation={hover.feature.properties.id}
      style={{ left: hover.x, top: hover.y }}>
      <small>{hover.feature.properties.source} · {hover.feature.properties.source_kind === "primary" ? "NISAR" : "complementario"}</small>
      <strong>{hover.feature.properties.title}</strong>
      <span>{hover.feature.properties.place}</span>
      <b>{metric.value == null ? "Cifra sin publicar" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: metric.decimals }).format(metric.value)} <small>{metric.unit}</small></b>
      <time dateTime={hover.feature.properties.date}>{formatDate(hover.feature.properties.date)}</time>
    </div>}
  </>;
}
