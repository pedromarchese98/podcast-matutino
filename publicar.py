#!/usr/bin/env python3
"""Agrega un episodio al podcast y regenera el feed RSS.

Uso:
  python3 publicar.py --mp3 /ruta/resumen-2026-11-12.mp3 --fecha 2026-11-12 \
      --titulo "Jueves 12 de noviembre" --descripcion "Inflación, Nvidia, Ucrania..."

Después hay que hacer commit y push; Vercel publica solo.
"""
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
SITIO = RAIZ / "public" / CONFIG["slug"]
EPISODIOS_DIR = SITIO / "episodios"
INDICE = RAIZ / "episodios.json"
BASE = f'{CONFIG["base_url"].rstrip("/")}/{CONFIG["slug"]}'
ARG = timezone(timedelta(hours=-3))


def duracion_segundos(mp3: Path) -> int:
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(salida))


def cargar() -> list:
    return json.loads(INDICE.read_text(encoding="utf-8")) if INDICE.exists() else []


def generar_feed(episodios: list) -> str:
    items = []
    for e in episodios:
        fecha = datetime.strptime(e["fecha"], "%Y-%m-%d").replace(hour=8, tzinfo=ARG)
        url = f'{BASE}/episodios/{e["archivo"]}'
        m, s = divmod(e["segundos"], 60)
        items.append(f"""    <item>
      <title>{escape(e["titulo"])}</title>
      <description>{escape(e["descripcion"])}</description>
      <itunes:summary>{escape(e["descripcion"])}</itunes:summary>
      <pubDate>{format_datetime(fecha)}</pubDate>
      <guid isPermaLink="false">podcast-matutino-{e["fecha"]}</guid>
      <enclosure url="{escape(url)}" length="{e["bytes"]}" type="audio/mpeg"/>
      <itunes:duration>{m}:{s:02d}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    titulo = escape(CONFIG["titulo"])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{titulo}</title>
    <link>{BASE}/</link>
    <atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>es-ar</language>
    <description>{escape(CONFIG["descripcion"])}</description>
    <itunes:author>{escape(CONFIG["autor"])}</itunes:author>
    <itunes:image href="{BASE}/portada.png"/>
    <image><url>{BASE}/portada.png</url><title>{titulo}</title><link>{BASE}/</link></image>
    <itunes:category text="News"><itunes:category text="Daily News"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>yes</itunes:block>
    <lastBuildDate>{format_datetime(datetime.now(ARG))}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mp3", required=True)
    p.add_argument("--fecha", required=True, help="AAAA-MM-DD")
    p.add_argument("--titulo", required=True)
    p.add_argument("--descripcion", required=True)
    a = p.parse_args()

    datetime.strptime(a.fecha, "%Y-%m-%d")
    origen = Path(a.mp3)
    EPISODIOS_DIR.mkdir(parents=True, exist_ok=True)
    archivo = f"{a.fecha}.mp3"
    destino = EPISODIOS_DIR / archivo
    if origen.resolve() != destino.resolve():
        shutil.copyfile(origen, destino)

    episodios = [e for e in cargar() if e["fecha"] != a.fecha]
    episodios.append({
        "fecha": a.fecha,
        "titulo": a.titulo,
        "descripcion": a.descripcion,
        "archivo": archivo,
        "bytes": destino.stat().st_size,
        "segundos": duracion_segundos(destino),
    })
    episodios.sort(key=lambda e: e["fecha"], reverse=True)

    # Se conservan solo los episodios más recientes.
    for viejo in episodios[CONFIG["max_episodios"]:]:
        (EPISODIOS_DIR / viejo["archivo"]).unlink(missing_ok=True)
    episodios = episodios[:CONFIG["max_episodios"]]

    INDICE.write_text(json.dumps(episodios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SITIO / "feed.xml").write_text(generar_feed(episodios), encoding="utf-8")
    print(f"OK: {len(episodios)} episodios. Feed: {BASE}/feed.xml")


if __name__ == "__main__":
    main()
