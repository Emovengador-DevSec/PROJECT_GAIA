import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type { AOI, CameraMode } from "../../lib/api";

type Props = { aoi?: AOI; tileUrl?: string; exaggeration: number; camera?: CameraMode };

/**
 * Globo 3D con vuelo cinematográfico. Con VITE_CESIUM_ION_TOKEN usa relieve mundial real;
 * sin token cae a un elipsoide (sigue funcionando sin red de Cesium ion).
 */
export function Globe({ aoi, tileUrl, exaggeration, camera = "oblique" }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer | null>(null);
  const overlay = useRef<Cesium.ImageryLayer | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const token = import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined;
    if (token) Cesium.Ion.defaultAccessToken = token;
    const v = new Cesium.Viewer(host.current, {
      animation: false, timeline: false, baseLayerPicker: false, geocoder: false,
      homeButton: false, sceneModePicker: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: false, selectionIndicator: false,
      baseLayer: token ? undefined : new Cesium.ImageryLayer(
        new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" })),
    });
    v.scene.globe.enableLighting = true;          // terminador día/noche realista
    v.scene.fog.enabled = true;
    if (v.scene.skyAtmosphere) v.scene.skyAtmosphere.show = true;
    if (token) Cesium.createWorldTerrainAsync().then((t) => { if (!v.isDestroyed()) v.terrainProvider = t; });
    v.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(-75, -10, 9_000_000) });
    viewer.current = v;
    return () => { v.destroy(); viewer.current = null; };
  }, []);

  useEffect(() => {
    const v = viewer.current;
    if (v) v.scene.verticalExaggeration = exaggeration;
  }, [exaggeration]);

  // Vuelo: órbita alta -> picada oblicua sobre la zona (el "momento" de la demo)
  useEffect(() => {
    const v = viewer.current;
    if (!v || !aoi) return;
    const [w, s, e, n] = aoi.bbox;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const cam = (aoi as AOI & { camera?: { heading_deg?: number; pitch_deg?: number } }).camera ?? {};
    const pad = camera === "overview" ? 6 : 0;
    const pitch = camera === "zone" ? -90 : camera === "overview" ? -60 : cam.pitch_deg ?? -38;
    v.camera.flyTo({
      destination: Cesium.Rectangle.fromDegrees(w - pad, s - pad, e + pad, n + pad),
      orientation: { heading: Cesium.Math.toRadians(cam.heading_deg ?? 20), pitch: Cesium.Math.toRadians(pitch), roll: 0 },
      duration: reduce ? 0 : 3.2,
      easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT,
    });
  }, [aoi, camera]);

  // Capa de datos NISAR (teselas COG desde TiTiler)
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    if (overlay.current) { v.imageryLayers.remove(overlay.current); overlay.current = null; }
    if (!tileUrl) return;
    overlay.current = v.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({ url: tileUrl, maximumLevel: 16 }));
    overlay.current.alpha = 0.85;
  }, [tileUrl]);

  return <div ref={host} className="globe" aria-label="Globo 3D con datos de radar" />;
}
