import {readFileSync,existsSync} from "node:fs";
import {describe,it,expect} from "vitest";
import type {AlertFeature} from "../src/lib/api";
import {exposureSummary} from "../src/features/workspace/ZoneSheetPanels";
const path=new URL("../../../data/04_published/exposure/ayacucho-huanta.json",import.meta.url);
describe.skipIf(!existsSync(path))("F7 exposure from actual observations",()=>{
 it("keeps missing population distinct from a measured zero",()=>{
  const data=JSON.parse(readFileSync(path,"utf8"));
  for(const exposure of Object.values(data.alerts) as any[]){
   const feature={properties:{exposure:{...exposure,people:exposure.population,crop_ha:exposure.cropland_ha}}} as AlertFeature;
   const text=exposureSummary(feature);
   if(exposure.population==null) expect(text).not.toMatch(/persona|Población/);
   else expect(text).toContain("personas estimadas");
   expect(text).not.toContain("undefined");
  }
 });
});
