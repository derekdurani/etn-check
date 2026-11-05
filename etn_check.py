#!/usr/bin/env python3
"""
Monitor de asientos ETN -> notificacion push via ntfy.sh

Carga la pagina real de resultados de ETN con un navegador headless (Playwright)
-tal como lo haria tu navegador- y lee la respuesta que el propio sitio pide a su
API. De ahi cuenta los asientos libres de cada salida real y manda una
notificacion a un topic de ntfy.sh.

Se usa un navegador real (no peticiones HTTP crudas) porque la API de ETN solo
responde a su propio frontend; este script no falsifica identidad ni evade nada:
simplemente abre la pagina publica y observa lo que carga.

Configuracion por variables de entorno:
  ETN_ORIGIN   slug de origen            (default: t-leon-central)
  ETN_DEST     slug de destino           (default: t-ciudad-victoria)
  ETN_DATE     fecha del viaje YYYY-MM-DD(default: 2026-11-21)
  ETN_LABEL    etiqueta legible          (default: "Leon -> Cd. Victoria")
  NTFY_SERVER  servidor ntfy             (default: https://ntfy.sh)
  NTFY_TOPIC   topic de ntfy             (REQUERIDO para notificar)

Requiere: playwright (pip install playwright && python -m playwright install chromium)
"""
import os
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

ORIGIN = os.environ.get("ETN_ORIGIN", "t-leon-central")
DEST = os.environ.get("ETN_DEST", "t-ciudad-victoria")
DATE = os.environ.get("ETN_DATE", "2026-11-21")  # YYYY-MM-DD (para la URL del sitio)
LABEL = os.environ.get("ETN_LABEL", "Leon -> Cd. Victoria")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

SEARCH_URL = (
    f"https://viajes.etn.com.mx/search/{ORIGIN}/{DEST}/{DATE}"
    f"/p/general-1/departures?seatsOnResultsDiscounts=true"
)
RESULT_RE = re.compile(r"/api/v2/search/\d+\?type=bus")


def fetch_result(timeout_s=60):
    """Abre la pagina y devuelve el JSON 'finished' de la busqueda, o None."""
    captured = {"data": None}

    def on_response(resp):
        if captured["data"] is not None:
            return
        try:
            if RESULT_RE.search(resp.url):
                j = resp.json()
                if j.get("state") == "finished" and j.get("trips") is not None:
                    captured["data"] = j
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="es-MX")
        page = context.new_page()
        page.on("response", on_response)
        try:
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=timeout_s * 1000)
        except Exception as e:
            print("Aviso: goto no completo del todo:", e, file=sys.stderr)
        # Espera a que llegue la respuesta 'finished'.
        for _ in range(timeout_s):
            if captured["data"] is not None:
                break
            page.wait_for_timeout(1000)
        browser.close()
    return captured["data"]


def hhmm(iso):
    return iso[11:16] if isinstance(iso, str) and len(iso) >= 16 else str(iso)


def build_message(result):
    trips = [t for t in result.get("trips", []) if not t.get("open_ticket")]
    if not trips:
        return f"Sin salidas disponibles para {LABEL} el {DATE}.", "ETN: sin salidas", 0

    trips.sort(key=lambda t: t.get("departure", ""))
    lines = []
    total_free = 0
    for t in trips:
        av = t.get("availability", 0)
        cap = t.get("capacity", "?")
        if isinstance(av, int):
            total_free += av
        lines.append(f"Salida {hhmm(t.get('departure'))}: {av} de {cap} asientos libres")

    body = f"ETN {LABEL} | {DATE}\n" + "\n".join(lines)
    title = f"ETN: {total_free} asientos libres"
    return body, title, total_free


def ntfy(body, title, tags="bus", priority="default"):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC no configurado. Mensaje que se habria enviado:\n")
        print(f"[{title}]\n{body}")
        return
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
    # Headers de ntfy en ASCII (sin acentos ni emojis en el titulo).
    req.add_header("Title", title.encode("ascii", "ignore").decode("ascii"))
    req.add_header("Tags", tags)
    req.add_header("Priority", priority)
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main():
    try:
        result = fetch_result()
        if not result:
            ntfy(
                f"No se pudo obtener la disponibilidad de ETN {LABEL} ({DATE}). "
                f"La pagina no devolvio resultados a tiempo.",
                "ETN: sin respuesta",
                tags="warning",
                priority="high",
            )
            print("Sin resultado 'finished'.", file=sys.stderr)
            return 1
        body, title, _ = build_message(result)
        ntfy(body, title)
        print("Notificacion enviada:\n", title, "\n", body)
        return 0
    except Exception as e:  # noqa: BLE001
        detail = f"Error al consultar ETN {LABEL} ({DATE}): {e}"
        try:
            ntfy(detail, "ETN: error", tags="warning", priority="high")
        except Exception:
            pass
        print(detail, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
