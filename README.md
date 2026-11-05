# Monitor de asientos ETN

Revisa automáticamente, **2 veces al día y sin tu computadora encendida**, cuántos
asientos quedan libres en una ruta/fecha de ETN y te manda una **notificación push**
al teléfono vía [ntfy.sh](https://ntfy.sh). Corre gratis en **GitHub Actions**.

Ruta configurada por defecto: **León (Central) → Ciudad Victoria, 21-nov-2026**.
Horario: **12:00 PM y 6:00 PM** (hora de México).

---

## Cómo funciona

GitHub Actions abre la página real de resultados de ETN con un navegador headless
(Playwright), lee la respuesta que el propio sitio pide a su API (incluye los
asientos disponibles de cada salida) y publica un mensaje en tu topic de ntfy.
Se usa un navegador real porque la API de ETN solo responde a su propio frontend.

Archivos:
- `etn_check.py` — el script.
- `.github/workflows/etn-monitor.yml` — el horario (cron) y los pasos.

---

## Configuración (una sola vez, ~10 min)

### 1. Instala la app ntfy y elige un topic
1. Instala **ntfy** en tu teléfono (App Store / Google Play) o usa la web.
2. Inventa un nombre de *topic* difícil de adivinar (cualquiera con ese nombre
   puede leer y publicar). Ejemplo: `etn-derek-7h3k9q2x`.
3. En la app, **Subscribe** a ese topic.

### 2. Crea el repositorio en GitHub
1. Crea un repo nuevo (puede ser **privado**).
2. Sube estos tres archivos respetando las carpetas:
   ```
   etn_check.py
   .github/workflows/etn-monitor.yml
   README.md
   ```

### 3. Guarda el topic como secreto
En el repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `NTFY_TOPIC`
- Secret: tu topic (ej. `etn-derek-7h3k9q2x`)

### 4. Prueba
En la pestaña **Actions** del repo, elige **ETN seat monitor → Run workflow**.
A los ~2 min debe llegarte la notificación con los asientos libres.

¡Listo! A partir de ahí corre solo a las 12 PM y 6 PM.

---

## Cambiar la ruta, fecha u horario

- **Ruta / fecha:** edita el bloque `env:` en `.github/workflows/etn-monitor.yml`
  (`ETN_ORIGIN`, `ETN_DEST`, `ETN_DATE` en formato `YYYY-MM-DD`, `ETN_LABEL`).
  Los *slugs* de origen/destino son los que aparecen en la URL de ETN
  (ej. `t-leon-central`, `t-ciudad-victoria`).
- **Horario:** cambia el `cron`. Es en **UTC**. México es UTC−6, así que
  resta/suma 6 horas. Ejemplos:
  - `0 0,18 * * *` → 6 PM y 12 PM México (actual)
  - `0 15 * * *` → 9 AM México, una vez al día
  - `0 1,13 * * *` → 7 PM y 7 AM México

## Notas

- GitHub puede retrasar las corridas programadas algunos minutos cuando hay mucha
  carga; no son al segundo exacto.
- GitHub **desactiva** los workflows programados si el repo pasa ~60 días sin
  actividad; si eso pasa, entra a Actions y reactívalo (o haz cualquier commit).
- Después de la fecha del viaje, la notificación dirá "Sin salidas disponibles".
- Si ETN cambia su sitio/API, el script podría necesitar ajustes.
