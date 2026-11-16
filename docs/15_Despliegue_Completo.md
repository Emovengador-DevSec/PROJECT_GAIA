# Despliegue de GAIA Alerta con la API en vivo

La imagen sirve React y FastAPI en el mismo dominio. FastAPI genera las teselas a partir de los COG NISAR y actualiza USGS y FIRMS. La caché muestra la fecha de observación cuando falla una fuente externa.

## Construcción y prueba local

Desde la raíz del proyecto, con Docker Desktop en modo Linux y el par activo ya procesado:

```powershell
uv run python tools/deploy/collect_runtime_data.py
docker build -t gaia-alerta .
docker run --rm --name gaia-alerta -p 127.0.0.1:7860:7860 --env-file .env gaia-alerta
```

El exportador genera `deploy/data/` con el par activo, la exposición, la validación, las capas visuales y los catálogos que consulta la API. El paquete probado ocupa 259,37 MB. El destino debe estar vacío y se crea con cada exportación. Para repetir el proceso se puede usar `--output deploy/otro-destino` y sustituir la copia local `deploy/data/` antes de compilar. Los HDF5 y el período de la trayectoria 75 permanecen en el archivo de trabajo.

La exportación también recoge comunidad, NASA POWER, pendientes agrícolas, historia MODIS y lluvia IMERG cuando están publicados. Los recortes ópticos HLS se cargan a petición. El tamaño cambia al añadir estas capas; usa la cifra que imprime el exportador.

Los reportes ciudadanos requieren un almacenamiento persistente en `/srv/gaia/data/reports`. En la validación local se monta `deploy/reports-runtime` en esa ruta. En el servicio de producción configura un volumen persistente y `GAIA_REPORTS_ADMIN_TOKEN` como secreto de ejecución. Así los reportes sobreviven al reemplazo del contenedor. No incluyas esa carpeta en la imagen ni en Git.

Para compilar con la configuración local de Cesium, usa `docker build --secret id=web_env,src=apps/web/.env -t gaia-alerta .`. Vite consume el archivo montado como secreto durante la compilación. Las credenciales del servidor se suministran al ejecutar el contenedor.

Abre [la aplicación local](http://127.0.0.1:7860/) y [el estado de la API](http://127.0.0.1:7860/api/health). Entra a Ayacucho, abre Cambios, mueve la cortina y consulta la ficha de exposición. En Observaciones revisa las fechas de USGS y FIRMS. Si añades Cesium en local, autoriza esa URL en un token de desarrollo.

## Publicación en un Space de Hugging Face (sin Docker local)

Hugging Face construye la imagen en la nube, así que no hace falta Docker en la PC.

1. Retira la copia anterior de `deploy/data/` y ejecuta `uv run python tools/deploy/collect_runtime_data.py`.
2. Ejecuta `uv run python tools/deploy/build_space.py --repo https://github.com/<usuario>/<repo>`. Se crea `deploy/space/` con el código, `deploy/data/`, el `README.md` del Space (`sdk: docker`, `app_port: 7860`) y `.gitattributes` con los binarios en LFS.
3. Crea el Space (SDK Docker) en Hugging Face. En **Settings → Variables and secrets**, añade estos secretos: `VITE_CESIUM_ION_TOKEN` para la compilación, y `FIRMS_MAP_KEY` y `EARTHDATA_TOKEN` para la ejecución.
4. Dentro de `deploy/space/`, ejecuta `git init`, `git lfs install`, `git remote add origin https://huggingface.co/spaces/<usuario>/<space>`, `git add .`, `git commit` y `git push -u origin main`. Hugging Face pide iniciar sesión: usa un token de escritura propio y no lo guardes en el proyecto.
5. Si actualizas los datos, repite los pasos 1 y 2. `build_space.py` conserva la carpeta `.git`, así que basta con hacer `git add .`, `git commit` y `git push`.

## Publicación

1. El propietario crea un repositorio para el código y un servicio Docker que sirva el puerto `7860` o que proporcione `PORT`. Si el servicio compila desde Git, el contexto del servicio debe incluir `deploy/data/` como artefacto de despliegue. Como alternativa, el servicio puede ejecutar la imagen ya construida desde un registro. `deploy/` está excluido de Git en el repositorio de código.
2. Añade `FIRMS_MAP_KEY` y `EARTHDATA_TOKEN` en los secretos de ejecución del servicio. Las imágenes procesadas se sirven desde los COG incluidos. La clave de Earthdata se usa para el acceso a productos originales.
3. Crea un token de Cesium ion de solo lectura para los recursos del mapa y añade el dominio HTTPS exacto en **Selected URLs**. En Hugging Face usa el dominio final `https://<space>.hf.space`. El token de Cesium se entrega al navegador. En una compilación local, configura `VITE_CESIUM_ION_TOKEN` en la sesión y ejecuta `docker build --secret id=VITE_CESIUM_ION_TOKEN,env=VITE_CESIUM_ION_TOKEN -t gaia-alerta .`. [Restricciones de Cesium ion](https://cesium.com/learn/ion/cesium-ion-access-tokens/#url-restrictions)
4. Verifica la URL pública desde escritorio y móvil. Comprueba la portada, el globo, los orígenes de las alertas y la comparación NISAR. En el servidor, el arranque en paralelo de USGS y FIRMS está activado y las teselas tienen un límite de 360 peticiones por minuto por cliente. Para aplicar ese límite por visitante detrás de un proxy propio, configura `FORWARDED_ALLOW_IPS` solo con las direcciones de tus proxies de confianza.

Hugging Face exige un plan de pago para crear Spaces Docker. CPU Basic tiene 2 vCPU, 16 GB de RAM y 50 GB de disco efímero. Un Space Docker necesita `sdk: docker` y `app_port: 7860` en el encabezado YAML de su README y acepta secretos para la compilación y la ejecución. En CPU Basic se suspende tras 48 horas de inactividad. Render permite un servicio web Docker gratuito de 512 MB y lo suspende tras 15 minutos sin tráfico. Se requiere medir el arranque y la memoria con el proveedor elegido. [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview) · [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker) · [Suspensión de Spaces](https://huggingface.co/docs/hub/spaces-gpus) · [Planes de Render](https://render.com/docs/compute-plans) · [Suspensión en Render](https://render.com/docs/free)
