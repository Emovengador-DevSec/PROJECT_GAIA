"""Constancia de evidencia satelital en formato PDF (Fase 3.4).

Genera un documento PDF válido estándar (PDF-1.4) sin dependencias externas,
utilizando la biblioteca estándar de Python.

Título honesto: «Constancia de evidencia satelital para respaldar un trámite».
No es un certificado oficial ni garantiza el pago del Seguro Agrícola Catastrófico
ni de MERESE o bonos de carbono; se presenta como evidencia técnica de apoyo.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class MinimalPDFBuilder:
    """Construye un archivo PDF-1.4 válido con soporte para texto, saltos de línea y tablas básicas."""

    def __init__(
        self,
        page_width: float = 595.28,
        page_height: float = 841.89,
    ) -> None:  # A4 en puntos tipográficos
        self.width = page_width
        self.height = page_height
        self.pages: list[list[str]] = [[]]
        self.current_page = 0
        self.y = page_height - 50.0  # Margen superior
        self.margin_x = 45.0
        self.content_width = page_width - (2 * self.margin_x)

    def new_page(self) -> None:
        self.pages.append([])
        self.current_page += 1
        self.y = self.height - 50.0

    def check_space(self, needed_pt: float) -> None:
        if self.y - needed_pt < 50.0:  # Margen inferior
            self.new_page()

    def add_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        line_width: float = 0.5,
        r: float = 0.6,
        g: float = 0.6,
        b: float = 0.6,
    ) -> None:
        cmd = f"{r:.2f} {g:.2f} {b:.2f} RG {line_width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        self.pages[self.current_page].append(cmd)

    def add_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        r: float = 0.95,
        g: float = 0.95,
        b: float = 0.95,
        fill: bool = True,
    ) -> None:
        if fill:
            cmd = f"{r:.2f} {g:.2f} {b:.2f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f"
        else:
            cmd = f"{r:.2f} {g:.2f} {b:.2f} RG 0.5 w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S"
        self.pages[self.current_page].append(cmd)

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        font: str = "F1",
        size: float = 10.0,
        r: float = 0.1,
        g: float = 0.1,
        b: float = 0.1,
    ) -> None:
        # Sanitizar texto para PDF (escapar paréntesis y barras invertidas, codificar latin-1 seguro)
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        # Caracteres no ASCII se reemplazan por equivalentes seguros en Latin-1
        safe_ascii = (
            safe.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
            .replace("ñ", "n").replace("Ñ", "N").replace("°", " deg").replace("·", "-").replace("«", "\"")
            .replace("»", "\"").replace("—", "-").replace("–", "-")
        )
        cmd = f"BT /{font} {size:.1f} Tf {r:.2f} {g:.2f} {b:.2f} rg {x:.2f} {y:.2f} Td ({safe_ascii}) Tj ET"
        self.pages[self.current_page].append(cmd)

    def add_paragraph(
        self,
        text: str,
        font: str = "F1",
        size: float = 9.0,
        leading: float = 12.0,
        r: float = 0.15,
        g: float = 0.15,
        b: float = 0.15,
        max_chars: int = 95,
    ) -> None:
        words = text.split(" ")
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > max_chars:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1
        if cur_line:
            lines.append(" ".join(cur_line))

        for line in lines:
            self.check_space(leading)
            self.draw_text(line, self.margin_x, self.y, font=font, size=size, r=r, g=g, b=b)
            self.y -= leading

    def add_kv(
        self,
        label: str,
        value: str,
        font_lbl: str = "F2",
        font_val: str = "F1",
        size: float = 9.0,
    ) -> None:
        self.check_space(14.0)
        self.draw_text(label, self.margin_x, self.y, font=font_lbl, size=size, r=0.2, g=0.2, b=0.2)
        val_x = self.margin_x + 155.0
        # Wrap value if needed
        words = value.split(" ")
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > 65:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1
        if cur_line:
            lines.append(" ".join(cur_line))

        first = True
        for line in lines:
            if not first:
                self.y -= 12.0
                self.check_space(12.0)
            self.draw_text(line, val_x, self.y, font=font_val, size=size, r=0.1, g=0.1, b=0.1)
            first = False
        self.y -= 14.0

    def compile(self) -> bytes:
        """Genera el flujo binario PDF-1.4 completo con tabla xref y catálogo."""
        objects: list[bytes] = []

        num_pages = len(self.pages)
        page_obj_ids = [3 + i for i in range(num_pages)]
        content_obj_ids = [3 + num_pages + i for i in range(num_pages)]
        f1_id = 3 + 2 * num_pages
        f2_id = f1_id + 1
        f3_id = f1_id + 2
        total_objs = f3_id

        # 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        # 2: Pages
        kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode())

        # Page objects
        for i in range(num_pages):
            cid = content_obj_ids[i]
            res_str = f"<< /Font << /F1 {f1_id} 0 R /F2 {f2_id} 0 R /F3 {f3_id} 0 R >> >>"
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Contents {cid} 0 R /Resources {res_str} >>"
            )
            objects.append(page_dict.encode())

        # Content streams
        for i, cmds in enumerate(self.pages):
            # Agregar pie de página en cada página
            footer_y = 30.0
            x2 = self.width - self.margin_x
            cmds.append(
                f"0.7 0.7 0.7 RG 0.5 w {self.margin_x:.2f} {footer_y + 10:.2f} m "
                f"{x2:.2f} {footer_y + 10:.2f} l S"
            )
            footer_text = f"GAIA Alerta - Pagina {i + 1} de {num_pages} - Evidencia Satelital NISAR"
            cmds.append(
                f"BT /F1 8 Tf 0.4 0.4 0.4 rg {self.margin_x:.2f} {footer_y:.2f} Td ({footer_text}) Tj ET"
            )

            stream_data = "\n".join(cmds).encode("latin-1", errors="replace")
            content_dict = (
                f"<< /Length {len(stream_data)} >>\nstream\n".encode() + stream_data + b"\nendstream"
            )
            objects.append(content_dict)

        # Fonts
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        # Construcción del PDF binario
        out = bytearray()
        out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]

        for i, obj in enumerate(objects):
            obj_id = i + 1
            offsets.append(len(out))
            out.extend(f"{obj_id} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {total_objs + 1}\n".encode())
        out.extend(b"0000000000 65535 f \n")
        for i in range(1, total_objs + 1):
            out.extend(f"{offsets[i]:010d} 00000 n \n".encode())

        out.extend(
            f"trailer\n<< /Size {total_objs + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
        )
        return bytes(out)


def generate_certificate_pdf(
    alert_feature: dict[str, Any],
    remediation_data: dict[str, Any] | None = None,
    aoi_id: str = "ayacucho-huanta",
) -> bytes:
    """Genera la constancia de evidencia satelital en PDF para una mancha específica."""
    p = alert_feature.get("properties", {})
    rem = remediation_data or p.get("remediation", {})
    metrics = p.get("metrics", {})

    # Manifiesto y hash SHA-256 para trazabilidad e integridad técnica
    manifest_bytes = json.dumps(alert_feature, sort_keys=True).encode("utf-8")
    sha256_hash = hashlib.sha256(manifest_bytes).hexdigest()
    emitted_at = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    pdf = MinimalPDFBuilder()

    # --- PÁGINA 1: IDENTIFICACIÓN, RADAR NISAR Y EXPOSICIÓN ---

    # Encabezado institucional
    pdf.draw_text(
        "GAIA ALERTA - PROYECTO DANCING WITH THE SARS",
        pdf.margin_x,
        pdf.y,
        font="F2",
        size=14,
        r=0.08,
        g=0.25,
        b=0.45,
    )
    pdf.y -= 18.0
    pdf.draw_text(
        "Constancia de Evidencia Satelital para Respaldar un Tramite",
        pdf.margin_x,
        pdf.y,
        font="F2",
        size=12,
        r=0.1,
        g=0.1,
        b=0.1,
    )
    pdf.y -= 14.0
    pdf.add_line(pdf.margin_x, pdf.y, pdf.width - pdf.margin_x, pdf.y, line_width=1.5, r=0.08, g=0.25, b=0.45)
    pdf.y -= 16.0

    # Cuadro de advertencia legal obligatorio
    pdf.add_rect(pdf.margin_x, pdf.y - 32, pdf.content_width, 42, r=0.96, g=0.96, b=0.98, fill=True)
    pdf.add_rect(pdf.margin_x, pdf.y - 32, pdf.content_width, 42, r=0.7, g=0.75, b=0.85, fill=False)
    pdf.draw_text(
        "AVISO LEGAL Y DE RESPALDO TECNICO:",
        pdf.margin_x + 8,
        pdf.y - 2,
        font="F2",
        size=8,
        r=0.2,
        g=0.2,
        b=0.2,
    )
    pdf.draw_text(
        "No es un certificado oficial ni garantiza el pago del Seguro Agricola Catastrofico ni de MERESE.",
        pdf.margin_x + 8,
        pdf.y - 14,
        font="F1",
        size=7.5,
        r=0.3,
        g=0.3,
        b=0.3,
    )
    pdf.draw_text(
        "Se presenta como evidencia tecnica satelital para apoyar tramites ante la agencia agraria o comuna.",
        pdf.margin_x + 8,
        pdf.y - 24,
        font="F1",
        size=7.5,
        r=0.3,
        g=0.3,
        b=0.3,
    )
    pdf.y -= 48.0

    # Sección 1: Identificación de la mancha
    sec1 = "1. IDENTIFICACION DEL AREA DE ESTUDIO"
    pdf.draw_text(sec1, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    pdf.add_kv("Codigo de Mancha (ID):", str(p.get("id", "alert_sin_id")))
    pdf.add_kv("Territorio / Cuenca (AOI):", f"{aoi_id} (Ayacucho - Huanta)")
    pdf.add_kv("Localidad o Sector:", str(p.get("place", "Sector rural de Ayacucho")))
    pdf.add_kv("Fecha de Emision de Ficha:", emitted_at)
    pdf.add_kv("Integridad SHA-256 (Hash):", sha256_hash[:32] + "...")
    pdf.y -= 8.0

    # Sección 2: Observación Radar NISAR
    sec2 = "2. PARAMETROS DE OBSERVACION RADAR (NISAR - FUENTE PRINCIPAL)"
    pdf.draw_text(sec2, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    nisar_sources = rem.get("sources_nisar", {})
    granules = nisar_sources.get("granules") or p.get("granules") or []
    dates = nisar_sources.get("dates") or p.get("date_range") or []
    if not granules or not dates:
        raise ValueError("Faltan gránulos o fechas NISAR: no se emite constancia sin procedencia")
    prod_name = f"{nisar_sources.get('product', 'NISAR GCOV L2')} (Dual HH/HV)"
    pdf.add_kv("Producto Satelital:", prod_name)
    pdf.add_kv("Fechas del Par de Analisis:", " -> ".join(dates) if isinstance(dates, list) else str(dates))
    for i, g in enumerate(granules[:2]):
        pdf.add_kv("Granulo de Origen:" if i == 0 else "", str(g))
    pdf.add_kv("Superficie Afectada (Mancha):", f"{metrics.get('area_ha', 0):.2f} hectareas (ha)")
    hv_drop = rem.get("factors", {}).get("hv_drop_db")
    pdf.add_kv(
        "Magnitud de Cambio Radar:",
        f"Caida HV media de {hv_drop:.1f} dB dentro de la mancha" if hv_drop is not None else "No medida",
    )
    lvl_str = f"{str(rem.get('level', '')).upper()} (Indice: {rem.get('index', 0) * 100:.0f}%)"
    pdf.add_kv("Nivel de Prioridad Calculado:", lvl_str)
    pdf.y -= 8.0

    # Sección 3: Evidencia Óptica Complementaria HLS y Terreno
    sec3 = "3. EVIDENCIA OPTICA COMPLEMENTARIA (NASA HLS S30) Y TOPOGRAFIA"
    pdf.draw_text(sec3, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    pdf.add_kv("Sensor Optico Complementario:", "HLS S30 v2.0 (Sentinel-2, 30 m) - NASA / USGS LP DAAC")
    pdf.add_kv("Fechas Opticas de Referencia:", "2026-06-22 (Antes) y 2026-10-08 (Despues)")
    pdf.add_kv("Indice NDVI:", "No calculado por mancha (solo imagen de color natural)")
    slope = rem.get("factors", {}).get("slope_deg")
    is_steep = slope and slope > 15
    slope_str = f"{slope:.1f} deg ({'Inclinada > 15 deg' if is_steep else 'Suave'})" if slope else "No medido"
    pdf.add_kv("Pendiente Topografica Media:", f"{slope_str} (Mapzen Terrain Tiles, 30 m)")
    crop_exp = p.get("exposure", {}).get("crop_ha") if p.get("exposure") else None
    crop_ha = crop_exp or rem.get("factors", {}).get("crop_ha", 0)
    pdf.add_kv("Cultivos en Zona de Mancha:", f"{crop_ha or 0:.2f} ha expuesto (ESA WorldCover 2021)")
    pdf.y -= 12.0

    # --- PÁGINA 2: RECETA SbN, COSTO-BENEFICIO, ESCENARIOS Y FIRMA ---
    pdf.new_page()

    # Sección 4: Diagnóstico y Receta de Restauración Natural (SbN)
    sec4 = "4. DIAGNOSTICO DE RIESGO Y RECETA DE RESTAURACION (SbN)"
    pdf.draw_text(sec4, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    pdf.add_kv("Diagnostico Principal:", str(rem.get("risk_name") or "Causa por verificar"))
    recipe = rem.get("recipe", {})
    if recipe:
        pdf.add_kv("Condicion del Terreno:", str(recipe.get("condition", "Laderas andinas")))
        species = recipe.get("species_primary", [])
        if species:
            pdf.add_kv("Especies Nativas Sugeridas:", ", ".join(species))
        if recipe.get("source"):
            pdf.add_kv("Fuente Tecnica de la Receta:", str(recipe["source"]))
    else:
        pdf.add_kv("Receta:", "Sin receta: ningun factor respalda una causa. Verificar en campo.")
    pdf.y -= 8.0

    # Sección 5: Presupuesto Estimado y Análisis Costo-Beneficio
    sec5_title = "5. PRESUPUESTO DE INTERVENCION Y COSTO-BENEFICIO FRENTE A INACCION"
    pdf.draw_text(sec5_title, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    budget = rem.get("budget", []) or []
    cost_total = sum(b.get("cost_total_soles") or 0 for b in budget)
    cost_benefit = rem.get("cost_benefit")
    if cost_total > 0:
        pdf.add_kv("Presupuesto Estimado SbN:", f"S/ {cost_total:,.2f} PEN")
        sources = sorted({str(b["source"]) for b in budget if b.get("cost_total_soles") and b.get("source")})
        pdf.add_kv("Fuente de Costos:", "; ".join(sources) or "Sin fuente")
    else:
        pdf.add_kv("Presupuesto Estimado SbN:", "Costo por confirmar (sin fuente verificada)")
    if cost_benefit:
        loss = cost_benefit["loss_avoided_annual_pen"]
        pdf.add_kv("Perdida Anual Evitada Estimada:", f"S/ {loss:,.2f} PEN")
        pdf.add_kv("Fuente del Valor Agricola:", str(cost_benefit.get("valuation_source", "")))
    else:
        pdf.add_kv("Costo-Beneficio:", "No se calcula hasta verificar costos y valor agricola")
    pdf.y -= 8.0

    # Sección 6: Escenario Proyectado a 3 y 5 Años
    sec6_title = "6. PROYECCION DE RECUPERACION VEGETAL (NDVI A 3 Y 5 ANOS)"
    pdf.draw_text(sec6_title, pdf.margin_x, pdf.y, font="F2", size=10, r=0.08, g=0.25, b=0.45)
    pdf.y -= 14.0
    rec_scen = rem.get("recovery_scenario") or {}
    scen_label = rec_scen.get(
        "mandatory_label",
        "Escenario con supuestos. No es una observacion ni una promesa.",
    )
    pdf.add_rect(pdf.margin_x, pdf.y - 12, pdf.content_width, 18, r=0.98, g=0.95, b=0.92, fill=True)
    pdf.draw_text(
        f"ETIQUETA FIJA: {scen_label}",
        pdf.margin_x + 6,
        pdf.y - 8,
        font="F2",
        size=7.5,
        r=0.6,
        g=0.3,
        b=0.1,
    )
    pdf.y -= 20.0
    proj = (rec_scen or {}).get("projected", {})
    if rec_scen.get("citation_status") == "verificado":
        for key, label in (("year_3", "3"), ("year_5", "5")):
            if proj.get(key):
                pdf.add_kv(
                    f"Ganancia relativa NDVI a {label} anos:",
                    f"+{proj[key]['gain_ndvi']:.2f} (supuesto)",
                )
        pdf.add_kv("Cita:", str(rec_scen.get("citation", "")))
    else:
        pdf.add_kv("Escenario:", "No incluido: falta una fuente verificada o una causa respaldada")
    pdf.y -= 12.0

    pdf.add_rect(pdf.margin_x, pdf.y - 36, pdf.content_width, 40, r=0.95, g=0.95, b=0.95, fill=True)
    pdf.draw_text(
        "CLAUSULA DE MONITOREO Y VERIFICACION EN CAMPO:",
        pdf.margin_x + 8,
        pdf.y - 4,
        font="F2",
        size=8,
        r=0.2,
        g=0.2,
        b=0.2,
    )
    pdf.draw_text(
        "Aviso de monitoreo. No reemplaza a INDECI ni a la autoridad local. Verificar en campo.",
        pdf.margin_x + 8, pdf.y - 16, font="F2", size=8, r=0.8, g=0.1, b=0.1,
    )
    pdf.draw_text(
        f"Manifiesto criptografico: SHA-256 = {sha256_hash}",
        pdf.margin_x + 8, pdf.y - 28, font="F3", size=7, r=0.3, g=0.3, b=0.3,
    )

    return pdf.compile()
