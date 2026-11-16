#!/usr/bin/env python3
"""Agrega un episodio a un curso por entregas y regenera su feed RSS.

Cada curso tiene su propio feed, separado del podcast diario. Su configuración
vive en cursos/<curso>.json y su índice de episodios en cursos/<curso>-episodios.json.

Uso:
  python3 publicar_curso.py --curso geopolitica --numero 1 --mp3 /ruta/episodio.mp3 \
      --titulo "Por qué chocan los Estados" --descripcion "Poder, seguridad e intereses..."

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
ARG = timezone(timedelta(hours=-3))


def duracion_segundos(mp3: Path) -> int:
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(salida))


def generar_feed(config: dict, base: str, episodios: list) -> str:
    items = []
    for e in episodios:
        url = f'{base}/episodios/{e["archivo"]}'
        m, s = divmod(e["segundos"], 60)
        titulo = f'{e["numero"]}. {e["titulo"]}'
        items.append(f"""    <item>
      <title>{escape(titulo)}</title>
      <description>{escape(e["descripcion"])}</description>
      <itunes:summary>{escape(e["descripcion"])}</itunes:summary>
      <pubDate>{e["publicado"]}</pubDate>
      <guid isPermaLink="false">curso-{config["curso"]}-{e["numero"]:02d}</guid>
      <enclosure url="{escape(url)}" length="{e["bytes"]}" type="audio/mpeg"/>
      <itunes:duration>{m}:{s:02d}</itunes:duration>
      <itunes:episode>{e["numero"]}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    titulo = escape(config["titulo"])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{titulo}</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>es-ar</language>
    <description>{escape(config["descripcion"])}</description>
    <itunes:author>{escape(config["autor"])}</itunes:author>
    <itunes:image href="{base}/portada.png"/>
    <image><url>{base}/portada.png</url><title>{titulo}</title><link>{base}/</link></image>
    <itunes:category text="Education"/>
    <itunes:type>serial</itunes:type>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>yes</itunes:block>
    <lastBuildDate>{format_datetime(datetime.now(ARG))}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--curso", required=True, help="nombre del archivo en cursos/, sin .json")
    p.add_argument("--numero", required=True, type=int)
    p.add_argument("--mp3", required=True)
    p.add_argument("--titulo", required=True)
    p.add_argument("--descripcion", required=True)
    a = p.parse_args()

    config = json.loads((RAIZ / "cursos" / f"{a.curso}.json").read_text(encoding="utf-8"))
    config["curso"] = a.curso
    sitio = RAIZ / "public" / config["slug"]
    episodios_dir = sitio / "episodios"
    indice = RAIZ / "cursos" / f"{a.curso}-episodios.json"
    base = f'{config["base_url"].rstrip("/")}/{config["slug"]}'

    episodios_dir.mkdir(parents=True, exist_ok=True)
    archivo = f"{a.numero:02d}.mp3"
    destino = episodios_dir / archivo
    if Path(a.mp3).resolve() != destino.resolve():
        shutil.copyfile(a.mp3, destino)

    episodios = json.loads(indice.read_text(encoding="utf-8")) if indice.exists() else []
    previo = next((e for e in episodios if e["numero"] == a.numero), None)
    episodios = [e for e in episodios if e["numero"] != a.numero]
    episodios.append({
        "numero": a.numero,
        "titulo": a.titulo,
        "descripcion": a.descripcion,
        "archivo": archivo,
        "bytes": destino.stat().st_size,
        "segundos": duracion_segundos(destino),
        # Se conserva la fecha original si el episodio se vuelve a subir.
        "publicado": previo["publicado"] if previo else format_datetime(datetime.now(ARG)),
    })
    episodios.sort(key=lambda e: e["numero"])

    indice.write_text(json.dumps(episodios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (sitio / "feed.xml").write_text(generar_feed(config, base, episodios), encoding="utf-8")
    print(f"OK: {len(episodios)} episodios. Feed: {base}/feed.xml")


if __name__ == "__main__":
    main()
