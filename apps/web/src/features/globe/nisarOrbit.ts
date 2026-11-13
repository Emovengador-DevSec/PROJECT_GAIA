import * as Cesium from "cesium";
import type { OMMJsonObject } from "satellite.js";
import { createPropagator, swathCenter } from "./orbitMath";

let correction: Promise<Record<string, Cesium.TranslationRotationScale>> | undefined;
function modelOrigin() {
  correction ??= fetch("/models/nisar.glb").then(response => {
    if (!response.ok) throw new Error("NISAR model unavailable");
    return response.arrayBuffer();
  }).then((buffer): Record<string, Cesium.TranslationRotationScale> => {
    const length = new DataView(buffer).getUint32(12, true);
    const gltf = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, length)));
    const root = gltf.nodes?.find((node: { name?: string }) => node.name === "NISAR");
    if (!root) return {};
    const [x, y, z, w] = root.rotation ?? [0, 0, 0, 1];
    // The existing cover asset carries its Blender scene placement. Cancel it at runtime
    // so minimumPixelSize scales the craft around the propagated position, not a distant origin.
    const original = root.matrix ? Cesium.Matrix4.fromArray(root.matrix)
      : Cesium.Matrix4.fromTranslationQuaternionRotationScale(
        Cesium.Cartesian3.fromArray(root.translation ?? [0, 0, 0]),
        new Cesium.Quaternion(x, y, z, w),
        Cesium.Cartesian3.fromArray(root.scale ?? [1, 1, 1]));
    const inverse = Cesium.Matrix4.inverse(original, new Cesium.Matrix4());
    return { NISAR: new Cesium.TranslationRotationScale(
      Cesium.Matrix4.getTranslation(inverse, new Cesium.Cartesian3()),
      Cesium.Quaternion.fromRotationMatrix(Cesium.Matrix4.getRotation(inverse, new Cesium.Matrix3())),
      Cesium.Matrix4.getScale(inverse, new Cesium.Cartesian3())) };
  });
  return correction;
}

export function addNisarOrbit(viewer: Cesium.Viewer, elements: OMMJsonObject, reduce: boolean) {
  const at = createPropagator(elements);
  const data = new Cesium.CustomDataSource("NISAR · CelesTrak · franja aproximada");
  const position = new Cesium.SampledPositionProperty();
  const start = Date.now();
  for (let time = start - 60_000; time <= start + 3 * 3_600_000; time += 20_000) {
    const p = at(time);
    if (p) position.addSample(Cesium.JulianDate.fromDate(new Date(time)), Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.height));
  }
  const satellite = data.entities.add({ id: "nisar-current", name: "NISAR · órbita calculada", position,
    orientation: new Cesium.VelocityOrientationProperty(position),
    model: { uri: "/models/nisar.glb", minimumPixelSize: 90, maximumScale: 200_000, scale: 1,
      show: false, enableVerticalExaggeration: false,
      silhouetteColor: Cesium.Color.fromCssColorString("#d5faff").withAlpha(.5), silhouetteSize: 1 },
    label: { text: "NISAR", font: "16px sans-serif", fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK, outlineWidth: 3, style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new Cesium.Cartesian2(0, -45), disableDepthTestDistance: Number.POSITIVE_INFINITY },
  });
  let disposed = false;
  modelOrigin().then(transforms => {
    if (disposed || viewer.isDestroyed()) return;
    satellite.model!.nodeTransformations = new Cesium.PropertyBag(transforms);
    satellite.model!.show = new Cesium.ConstantProperty(true);
  }).catch(() => {
    if (!disposed && !viewer.isDestroyed()) satellite.point = new Cesium.PointGraphics({
      pixelSize: 8, color: Cesium.Color.fromCssColorString("#c8f7fc"),
    });
  });
  const trajectory: Cesium.Cartesian3[] = [], ground: Cesium.Cartesian3[] = [];
  const period = 86_400_000 / Number(elements.MEAN_MOTION);
  for (let time = start; time <= start + period; time += 20_000) {
    const p = at(time);
    if (!p) continue;
    trajectory.push(Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.height));
    ground.push(Cesium.Cartesian3.fromDegrees(p.lon, p.lat));
  }
  data.entities.add({ polyline: { positions: trajectory, width: 1.4, material: Cesium.Color.WHITE.withAlpha(.4) } });
  data.entities.add({ polyline: { positions: ground, width: 1.4, clampToGround: true,
    material: Cesium.Color.fromCssColorString("#84dbe6").withAlpha(.65) } });
  const footprint = data.entities.add({ corridor: { positions: [], width: 240_000,
    material: Cesium.Color.fromCssColorString("#a7e8ef").withAlpha(.2), outline: true,
    outlineColor: Cesium.Color.fromCssColorString("#c8f7fc").withAlpha(.6), height: 0 } });
  let last = 0;
  const update = () => {
    const time = reduce ? start : Date.now();
    if (time - last < 1000) return;
    last = time;
    const positions: Cesium.Cartesian3[] = [];
    for (const offset of [-15_000, 0, 15_000]) {
      const p = at(time + offset), next = at(time + offset + 5000);
      if (p && next) {
        const center = swathCenter(p, next);
        positions.push(Cesium.Cartesian3.fromDegrees(center.lon, center.lat));
      }
    }
    footprint.corridor!.positions = new Cesium.ConstantProperty(positions);
  };
  update();
  viewer.dataSources.add(data);
  const removeFrame = viewer.scene.preRender.addEventListener(update);
  return {
    focus() {
      const point = position.getValue(viewer.clock.currentTime);
      if (point) viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(point, 0), {
        offset: new Cesium.HeadingPitchRange(0, -.65, 2_500_000), duration: reduce ? 0 : 2.4,
      });
    },
    dispose() {
      disposed = true;
      removeFrame();
      if (!viewer.isDestroyed()) viewer.dataSources.remove(data, true);
    },
    satellite,
  };
}
