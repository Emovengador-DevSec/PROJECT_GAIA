# Publicación estática de GAIA

G9 prepara una copia fechada de las observaciones y las imágenes procesadas para alojarla
en Cloudflare Pages. El globo, las fichas, las historias, la calidad y la cortina consultan
archivos de `snapshot/`. La fecha de la foto se muestra en la barra y en Calidad.

## Paquete comprobado

La foto se generó el 13 de noviembre de 2026 a las 23.46, hora de Perú,
equivalente a `2026-11-14T04:46:09+00:00`. Conserva por separado las fechas de observación
y consulta de USGS, FIRMS, NISAR, OPERA y las capas de exposición. Una nueva ejecución
del exportador actualiza los archivos y la fecha de la foto.

| Elemento | Resultado |
|---|---|
| Datos y teselas exportados | 2.903 archivos, unos 278,8 MB |
| Compilación completa | 3.276 archivos, unos 342,3 MB |
| Archivo más grande de la compilación | Por debajo de 25 MiB |
| Teselas NISAR | 2.840 PNG, niveles 0–13, antes/después y cambio HH/HV |
| Procedencia y calidad | Gránulos, fechas, madurez, método y cobertura de G1 conservados |
| Datos de Ayacucho | Trayectoria 147, 24-jun y 10-oct, 99,91 % de cobertura común |

La prueba de Chrome con la API apagada recorrió las cuatro zonas, abrió fichas con
exposición y comprobó las teselas de cambio, antes y después. En 1440×900 y 390×844
hubo cero llamadas a `/api`, cero respuestas HTTP de error y cero errores JavaScript.
La fecha coincidió entre la barra y Calidad y el rango temporal terminó en el instante
del manifiesto. El modo live se comprobó después y siguió consultando `/api` con la
API restaurada. Los informes y capturas están en `art/verificacion/G9/`.

El nivel 13 representa aproximadamente 19 m por píxel Web Mercator a la latitud del caso,
acorde con la rejilla NISAR de 20 m. Cesium amplía la última tesela disponible al acercarse.
Las imágenes usan las mismas escalas y paletas de la API. La línea de tiempo termina
en la fecha de la foto. La compilación estática usa los mapas NASA y el relieve regional
locales incluidos en el proyecto.

Cloudflare Pages Free admite 20.000 archivos por sitio y 25 MiB por archivo. Este paquete
cumple ambos límites y su archivo más grande pesa 12,3 MB. Para despliegues por CLI,
Vercel documenta un máximo de 100 MB de archivos fuente en Hobby y 1 GB en Pro.
El paquete supera ese límite de CLI en Hobby. Los límites se consultaron el 14 de
noviembre de 2026.
[Límites de Cloudflare](https://developers.cloudflare.com/pages/platform/limits/),
[Límites de Vercel](https://vercel.com/docs/limits#static-file-uploads)

## Generar una foto nueva

Desde la raíz del proyecto, inicia la API en una terminal de PowerShell y mantenla abierta.

```powershell
.venv\Scripts\python.exe -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000
```

En otra terminal de la misma carpeta ejecuta el exportador.

```powershell
.venv\Scripts\python.exe tools\snapshot_static.py
```

El proceso consulta la API de la PC. Guarda los JSON de todas las zonas, las imágenes de
contexto disponibles y los PNG NISAR. Comprueba campos sensibles, URLs firmadas y rutas
privadas antes de publicar cada JSON. Si ocurre un error, conserva la foto anterior.
El manifiesto registra fecha UTC, rutas, tamaños y SHA-256 de los archivos exportados.
Su lista y `total_bytes` describen los archivos de datos e imágenes y excluyen al propio
`manifest.json` para evitar una referencia circular.

Al terminar, detén la API con Ctrl+C para comprobar la versión estática por separado.

## Compilar y abrir en la PC

En PowerShell desde la raíz del proyecto ejecuta los siguientes comandos. La carpeta
`dist-static` permite conservar la compilación local de la demo en vivo.

```powershell
$env:VITE_DATA_MODE='static'
npm --prefix apps/web run build -- --outDir dist-static
Remove-Item Env:VITE_DATA_MODE
npm --prefix apps/web run preview -- --outDir dist-static --host 127.0.0.1 --port 4173
```

Abre `http://127.0.0.1:4173`. La barra debe mostrar «Datos actualizados al … · foto estática».
Entra en Lugares, abre Huanta y La Mar y recorre Historia, Cambios, Calidad y las fichas.
La cortina y los controles de polarización deben conservar la comparación real de G1.
`node tools/verify/static.mjs` repite la comprobación automática en Chrome a 1440 y 390 px,
con la API del puerto 8000 apagada.

La demo local habitual usa `VITE_DATA_MODE=live`, que también es el valor por defecto.
Ejecuta `npm --prefix apps/web run dev` y en otra terminal la API para conservar su
actualización de fuentes y su comportamiento de consulta en vivo.

## Conectar Cloudflare Pages al repositorio

La persona del equipo crea el repositorio público en GitHub y sube el proyecto completo.
Incluye `apps/web/public/snapshot/`, los recursos públicos de la portada y las atribuciones.
El repositorio ignora las credenciales locales, los HDF5 y los datos de trabajo originales.

1. En Cloudflare, abre Workers & Pages y crea un proyecto Pages conectado a Git.
2. Autoriza GitHub y elige el repositorio de GAIA y la rama que usarás para publicar.
3. Configura el directorio raíz como `apps/web`, el comando de compilación como
   `npm ci && npm run build` y la salida como `dist`.
4. Añade la variable de compilación `VITE_DATA_MODE` con valor `static` en producción.
   Usa el mismo valor en previews para que ambas compilaciones lean la foto.
5. Publica y abre la dirección HTTPS asignada por Pages. Comprueba la portada, la
   fecha, las fichas y ambas mitades de la cortina desde una ventana privada.

El exportador se ejecuta en la PC antes de subir una foto nueva al repositorio. La
compilación de Pages toma esa copia versionada y produce los archivos del sitio.
[Integración Git de Pages](https://developers.cloudflare.com/pages/get-started/git-integration/),
[Configuración de compilación](https://developers.cloudflare.com/pages/configuration/build-configuration/)

Para Vercel, importa el mismo repositorio con preset Vite, raíz `apps/web`, comando
`npm run build`, salida `dist` y `VITE_DATA_MODE=static`. Revisa primero el límite de
subida del plan elegido, dado el tamaño de este paquete.
[Vite en Vercel](https://vercel.com/docs/frameworks/frontend/vite)

## Credenciales y dominio de Cesium

El exportador obtiene datos públicos de la API local y omite las rutas de los COG del
servidor. La compilación estática elimina el token Cesium del usuario mediante una
condición de compilación y usa los recursos locales. La dependencia Cesium conserva
su cadena pública predeterminada, identificada en la revisión como parte de su código.
Earthdata y FIRMS permanecen en la configuración del servidor local.

Si se prepara después una publicación que consulte Cesium ion, crea en Cesium un
token de lectura con los activos necesarios y limita sus Allowed URLs al dominio HTTPS
asignado por Pages o Vercel. Mantén permisos mínimos y agrega las direcciones de
desarrollo que realmente se usen. Ese token público viaja al navegador según el diseño
de Cesium. La restricción se configura desde la cuenta de la persona del equipo cuando
conoce su dominio final.
[Control de acceso de Cesium ion](https://cesium.com/learn/ion/cesium-ion-access-tokens/)

## Actualizaciones y entrega

Al actualizar G1 o las observaciones complementarias, vuelve a generar la foto, compila
en modo estático y repite la verificación con la API apagada. Confirma los archivos
generados en Git y deja que Pages compile la nueva versión.

El enlace público queda pendiente de conectar el repositorio a la cuenta de alojamiento.
La copia local está preparada para esa publicación. Conserva también la demo en vivo
y el video de respaldo de G7 para la presentación.
