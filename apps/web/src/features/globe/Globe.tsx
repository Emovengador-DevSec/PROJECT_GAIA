import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type { AOI, AlertFeature, CameraMode, GlobeStatus } from "../../lib/api";
import { loadAyacuchoTerrain } from "./localTerrain";

type Props = {
  aoi?: AOI; tileUrl?: string; beforeUrl?: string; afterUrl?: string; split: number;
  contextOverlay?: { url: string; credit: string; beforeUrl?: string };
  exaggeration: number; camera?: CameraMode; alerts: AlertFeature[]; selected?: AlertFeature;
  offline?: boolean;
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

export function Globe({ aoi, tileUrl, beforeUrl, afterUrl, contextOverlay, split, exaggeration, camera = "oblique",
  alerts, selected, onSelect, onStatus, offline = false }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer | null>(null);
  const selectRef = useRef(onSelect);
  const statusRef = useRef(onStatus);
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
    v.scene.globe.dynamicAtmosphereLighting = true;
    v.scene.globe.maximumScreenSpaceError = 1.5;
    v.scene.highDynamicRange = true;
    v.scene.postProcessStages.fxaa.enabled = true;
    v.scene.fog.enabled = true;
    if (v.scene.skyAtmosphere) v.scene.skyAtmosphere.show = true;
    v.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(-70, -15, 13_500_000) });
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
      if (!v.isDestroyed()) v.imageryLayers.add(new Cesium.ImageryLayer(night, { dayAlpha: 0, nightAlpha: 1 }), nightIndex);
    };
    addBase().catch(() => {
      if (!v.isDestroyed() && v.imageryLayers.length === 0) { imagery = "No se pudo cargar la imagen satelital"; publish(); }
    });
    const localTerrain = () => loadAyacuchoTerrain().then(provider => {
      if (!v.isDestroyed()) { v.terrainProvider = provider; terrain = "regional"; publish(); }
    }).catch(() => { if (!v.isDestroyed()) { terrain = "unavailable"; publish(); } });
    if (token) Cesium.createWorldTerrainAsync({ requestVertexNormals: true }).then(provider => {
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
          label: { text, font: "14px sans-serif", fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK, outlineWidth: 3, style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(8, -10), horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1_500_000),
            disableDepthTestDistance: Number.POSITIVE_INFINITY },
        });
      }
    }).catch(() => { /* La imagen satelital sigue disponible. */ });
    const clicks = new Cesium.ScreenSpaceEventHandler(v.scene.canvas);
    clicks.setInputAction((event: { position: Cesium.Cartesian2 }) => {
      const picked = v.scene.pick(event.position);
      const feature = picked?.id?.properties?.alert?.getValue(v.clock.currentTime) as AlertFeature | undefined;
      if (feature) selectRef.current(feature);
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => { window.removeEventListener("resize", resize); clicks.destroy(); v.destroy(); viewer.current = null; };
  }, [offline]);

  useEffect(() => { if (viewer.current) viewer.current.scene.verticalExaggeration = exaggeration; }, [exaggeration, offline]);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    if (!aoi) {
      v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(-70, -15, 13_500_000),
        duration: window.matchMedia(REDUCED).matches ? 0 : 2 });
      return;
    }
    const [w, s, e, n] = aoi.bbox;
    const cam = aoi.camera ?? {};
    const pad = camera === "overview" ? 6 : 0;
    v.camera.flyTo({ destination: Cesium.Rectangle.fromDegrees(w - pad, s - pad, e + pad, n + pad),
      orientation: { heading: Cesium.Math.toRadians(cam.heading_deg ?? 20),
        pitch: Cesium.Math.toRadians(camera === "zone" ? -90 : camera === "overview" ? -60 : cam.pitch_deg ?? -38), roll: 0 },
      duration: window.matchMedia(REDUCED).matches ? 0 : 2.4, easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT });
  }, [aoi, camera, offline]);

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
    data.clustering.enabled = true;
    data.clustering.pixelRange = 38;
    data.clustering.minimumClusterSize = 4;
    data.clustering.clusterEvent.addEventListener((_entities, cluster) => {
      cluster.label.fillColor = Cesium.Color.fromCssColorString("#fbbf24");
      cluster.label.font = "600 15px sans-serif";
      cluster.label.showBackground = true;
      cluster.label.backgroundColor = Cesium.Color.fromCssColorString("#0c1219").withAlpha(.9);
      cluster.label.backgroundPadding = new Cesium.Cartesian2(8, 5);
      cluster.label.disableDepthTestDistance = Number.POSITIVE_INFINITY;
    });
    for (const feature of alerts.slice(0, 2500)) {
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
      data.entities.add({ id: p.id, name: p.title,
        position: Cesium.Cartesian3.fromDegrees(lon, lat), properties: { alert: feature },
        billboard: { image: marker(p.kind, COLORS[p.kind] ?? COLORS.surface_change), width: size, height: size,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY },
      });
    }
    v.dataSources.add(data);
    return () => { if (!v.isDestroyed()) v.dataSources.remove(data, true); };
  }, [alerts, offline]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || !selected?.geometry) return;
    let active = true;
    let polygon: Cesium.GeoJsonDataSource | undefined;
    const color = Cesium.Color.fromCssColorString(COLORS[selected.properties.kind] ?? COLORS.surface_change);
    if (selected.geometry.type === "Point") {
      const [lon, lat] = selected.geometry.coordinates as number[];
      v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(lon, lat, selected.properties.kind === "quake" ? 500_000 : 45_000),
        duration: window.matchMedia(REDUCED).matches ? 0 : 2 });
    } else {
      Cesium.GeoJsonDataSource.load(selected, { clampToGround: true, fill: color.withAlpha(.35), stroke: color, strokeWidth: 2 }).then(data => {
        if (!active || v.isDestroyed()) return;
        polygon = data;
        v.dataSources.add(data);
        v.flyTo(data, { duration: window.matchMedia(REDUCED).matches ? 0 : 2 });
      }).catch(() => { /* La ficha conserva la procedencia aunque una geometría sea inválida. */ });
    }
    return () => { active = false; if (polygon && !v.isDestroyed()) v.dataSources.remove(polygon, true); };
  }, [selected, offline]);

  return <div ref={host} className="globe" aria-label="Globo satelital de Sudamérica con observaciones georreferenciadas" />;
}
