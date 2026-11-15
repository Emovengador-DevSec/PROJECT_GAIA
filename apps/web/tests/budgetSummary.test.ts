import {readFileSync,existsSync} from "node:fs";
import {describe,it,expect} from "vitest";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import type {RemediationData} from "../src/lib/api";
import {BudgetSummary} from "../src/features/workspace/BudgetSummary";
const path=new URL("../../../data/04_published/remediation/ayacucho-huanta.json",import.meta.url);
describe.skipIf(!existsSync(path))("F5 actual published budgets",()=>{
  it("does not show raw placeholders, money gaps or unverified discounts",()=>{
    const data:RemediationData=JSON.parse(readFileSync(path,"utf8"));
    for(const zone of data.alerts){
      const html=renderToStaticMarkup(createElement(BudgetSummary,{items:zone.budget}));
      expect(html).not.toContain("por_verificar");
      expect(html).not.toContain("Sin dato");
      if(zone.budget.every(item=>item.status!=="verificado")){
        expect(html).not.toContain("Fuente:");
        expect(html).not.toContain("Descuento");
      }
    }
  });
});
