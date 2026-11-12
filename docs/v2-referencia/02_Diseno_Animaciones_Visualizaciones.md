# Diseño, animaciones y visualizaciones

Qué aspecto tiene la app y cómo se mueve. Estructura de pantallas en `01_Producto_Pestanas_Filtros.md`.

## Concepto visual: las franjas

El rasgo propio del radar interferométrico son las **franjas**: anillos de color que se repiten alrededor de un volcán o una falla y que miden movimiento. Esa imagen es la firma de la app.

- Lo único memorable es **un momento**: al abrir una zona, las franjas se expanden desde el centro y revelan el dato real. Todo lo demás es sobrio.
- La interfaz es oscura y callada para que el color de los datos sea lo más brillante de la pantalla.
- Las franjas decorativas usan la rampa de marca. **Los datos científicos nunca usan la rampa de marca**, salvo la fase envuelta, que es cíclica por naturaleza.

## Paleta

| Nombre | Hex | Uso |
|---|---|---|
| Abismo | `#0B1724` | Fondo del lienzo y de la app |
| Quebrada | `#14293B` | Superficies: riel, inspector, hojas |
| Cordillera | `#2B4A63` | Bordes, divisores, estados inactivos |
| Neblina | `#E6EDF3` | Texto principal |
| Escarcha | `#93A9BA` | Texto secundario y etiquetas |
| Eco | `#5BC0EB` | Acción principal, selección, foco |
| Ámbar | `#F4A259` | Severidad media y avisos de calidad |
| Alerta | `#E5484D` | Severidad alta y errores |

**Rampa de franjas (cíclica, solo marca y fase envuelta):** `#F25F5C` → `#FFE066` → `#70C1B3` → `#247BA0` → `#8E6BBF` → vuelve a `#F25F5C`.

**Tema claro "papel de campo"** solo para el informe PDF: fondo `#F7F8FA`, texto `#0B1724`, misma lógica de acentos con contraste verificado.

```css
:root {
  --abismo: #0B1724;
  --quebrada: #14293B;
  --cordillera: #2B4A63;
  --neblina: #E6EDF3;
  --escarcha: #93A9BA;
  --eco: #5BC0EB;
  --ambar: #F4A259;
  --alerta: #E5484D;
  --franja: conic-gradient(from 0deg, #F25F5C, #FFE066, #70C1B3, #247BA0, #8E6BBF, #F25F5C);
  --r-sm: 4px;   /* controles */
  --r-md: 8px;   /* paneles */
  --r-lg: 16px;  /* hojas flotantes */
}
```

Radios y sombras **cambian según la jerarquía**: nada de todos los elementos con el mismo borde redondeado y la misma sombra.

## Tipografía

| Rol | Familia | Notas |
|---|---|---|
| Títulos y números grandes | **Bricolage Grotesque** | Pesos 600 y 700, ligeramente ajustada |
| Texto e interfaz | **Source Sans 3** | Pesos 400 y 600, cifras tabulares activadas |

- Escala: 12, 14, 16, 20, 28, 40 px, con altura de línea 1,5 en texto.
- Línea de texto de **menos de 80 caracteres**.
- Cifras con `font-variant-numeric: tabular-nums` para que las leyendas no bailen.
- Sin mayúsculas sostenidas en etiquetas, sin subtítulos decorativos sobre cada encabezado, sin flechas añadidas a los botones.

## Composición

- **Lienzo a sangre:** el mapa ocupa todo; los paneles flotan encima y se pliegan.
- **Alineación:** texto a la izquierda. Los números de las leyendas, a la derecha.
- **Riel izquierdo** estrecho (ícono más nombre). **Inspector derecho** de 320 a 380 px.
- **Línea de tiempo inferior** con marcas por pasada NISAR y botón de reproducir.
- Elementos con peso distinto: el caso estrella es más grande en **Casos**; las alertas son filas con una **barra lateral de severidad**, no tarjetas idénticas.

## Mapas de color por variable

| Variable | Paleta | Por qué |
|---|---|---|
| Retrodispersión (dB) | Escala de grises | Se lee como una foto en blanco y negro |
| Compuesto HH, HV, HH/HV | Falso color RGB | Separa cubiertas por tono |
| Diferencia en dB entre fechas | Divergente rojo, blanco, azul (RdBu), centrada en 0 | El blanco es "sin cambio" |
| Desplazamiento (cm) | Divergente, simétrica alrededor de 0 | Acercamiento y alejamiento se distinguen |
| Coherencia (0 a 1) | Secuencial perceptual (viridis o cividis) | Apta para daltonismo |
| Fase envuelta | Cíclica (rampa de franjas) | Cada ciclo equivale a unos 12 cm en banda L |
| Clases (deslizamiento, deforestación...) | Paleta categórica apta para daltonismo (Okabe-Ito) | Distinguible sin depender del rojo y verde |
| Severidad | Neblina, Ámbar, Alerta, con ícono y texto | Nunca solo color |

**Reglas de leyenda:** unidades visibles, valores mínimo y máximo reales, marca del cero en las divergentes, nota "sin datos" y "enmascarado por baja coherencia" como entradas propias.

## Animaciones

Principio: **el movimiento responde a una acción o señala un hallazgo.** Nada se anima solo por decorar.

| Nombre | Disparador | Duración | Qué muestra | Biblioteca |
|---|---|---|---|---|
| Despertar de franjas | Abrir una zona por primera vez | 1,2 s, una vez | Franjas que se expanden desde el centro y revelan la capa | Canvas o Framer Motion |
| Reproducir tiempo | Botón en la línea de tiempo | Según pasadas | Avanza pasada por pasada, con transición suave entre capas | deck.gl o MapLibre |
| Cortina antes/después | Arrastrar el divisor | Inmediata | Revela una capa sobre otra | CSS y puntero |
| Vuelo a alerta | Elegir una alerta | 1,5 s | La cámara viaja a la zona | MapLibre o Cesium |
| Pulso de alerta | Alerta nueva o seleccionada | 2 repeticiones | Anillo que señala el punto | CSS |
| Progreso real | Descarga y procesamiento | Continua | Etapas: buscar, descargar, leer, convertir, listo | Framer Motion |
| Contador | Cambia una cifra clave | 400 ms | La cifra sube o baja hasta el nuevo valor | Framer Motion |
| Hoja y paneles | Abrir o cerrar inspector y hojas | 200 ms | Desliza con inercia suave | Framer Motion |
| Franjas de espera | Carga larga | Continua | Anillos tenues, no un círculo giratorio | CSS |

- **Curvas:** entrada con `ease-out`, salida con `ease-in`, nunca `linear` salvo la reproducción del tiempo.
- **`prefers-reduced-motion`:** el despertar se vuelve un fundido breve, los pulsos se detienen y la reproducción pasa a pasos manuales.
- **Presupuesto:** animaciones a 60 fotogramas por segundo en un portátil medio. Si no se logra, reducir calidad antes que bloquear el hilo.

## Visualizaciones

| Visualización | Pestaña | Tipo | Notas |
|---|---|---|---|
| Mapa ráster con paleta | Explorar, Cambios | Teselas COG | Paleta aplicada al dibujar |
| Cortina antes/después | Cambios | Dos capas con máscara | Dos fechas rotuladas |
| Histograma de cambio | Cambios | Barras | Umbral arrastrable, rango en dB |
| Zonas detectadas | Cambios, Alertas | Polígonos | Color por tipo, borde por severidad |
| Interferograma con franjas | Deformación | Ráster cíclico | Leyenda: un ciclo ≈ 12 cm |
| Perfil de desplazamiento | Deformación | Línea | Trazo del usuario, eje en cm |
| Terreno con capa | Relieve 3D | Terreno y textura | Exageración ajustable |
| Serie temporal con incertidumbre | Series de tiempo | Línea más banda | Punto central y banda, marcas de pasadas |
| Tendencia y saltos | Series de tiempo | Línea de ajuste | Saltos marcados como eventos |
| Huellas de pasadas | Catálogo | Polígonos coloreados | Color por número de pasadas |
| Línea de procedencia | Calidad | Cronología | Qué pasadas alimentan cada resultado |
| Ficha de calidad | Calidad | Barras de proporción | Área útil, enmascarada, sin datos |

Para gráficos usa Visx o D3. Para mapas, MapLibre más deck.gl. Para 3D, CesiumJS.

## Accesibilidad y adaptación

- Contraste mínimo AA en texto sobre `Abismo` y `Quebrada`.
- Foco visible en todos los controles, orden de tabulación lógico, atajos documentados.
- Gráficos con descripción textual y tabla de datos alternativa.
- Responsive: riel inferior en móvil, inspector como hoja, 3D reducido por defecto.
- Modo para daltonismo en **Ajustes**, que cambia las paletas divergentes y categóricas.

## Texto de la interfaz

- Español, minúscula de oración, verbos activos y claros.
- Un botón dice qué hace ("Exportar alertas") y su confirmación repite el verbo ("Alertas exportadas").
- Errores: qué pasó, por qué y cómo seguir. Ejemplo: "No hay pasadas de NISAR en esta zona antes del 17 de junio de 2026. Prueba con fechas posteriores o abre el catálogo."
- Vacíos: invitan a actuar. Ejemplo: "Aún no hay zona elegida. Dibuja un rectángulo en el mapa para empezar."
- Avisos de calidad con lenguaje llano: "Este dato es provisional y puede contener errores."

## Verificación visual

Antes de dar por terminada una pantalla: captura en escritorio y móvil, revisa contraste, revisa que ninguna paleta científica use la rampa de marca y quita un adorno que no sirva al dato.
