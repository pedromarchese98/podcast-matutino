#!/usr/bin/env python3
"""Graba un guion (podcast diario o curso) con la voz elegida (voz 2) y lo deja en MP3.

Graba oración por oración y controla el ritmo de cada una: con esta voz, el motor
a veces estira una oración de más. Las que salen demasiado lentas se vuelven a grabar.

Uso: python3 grabar.py guion.txt salida.mp3 ruta/al/modelo.onnx

El guion tiene un párrafo por línea; las líneas cortas se tratan como títulos de sección.
"""
import re
import statistics
import subprocess
import sys
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

LIMITE = 1.25   # una oración se regraba si tarda más de 1,25 veces lo normal
REINTENTOS = 6

guion, salida, MODELO = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
lineas = [l.strip() for l in guion.read_text(encoding="utf-8").splitlines() if l.strip()]
voz = PiperVoice.load(MODELO)
cfg = SynthesisConfig(length_scale=1.06, noise_scale=0.85, noise_w_scale=1.0)
sr = voz.config.sample_rate


def grabar(texto: str) -> bytes:
    return b"".join(c.audio_int16_bytes for c in voz.synthesize(texto, syn_config=cfg))


# Cada elemento: [línea, oración, audio]
piezas = []
for i, l in enumerate(lineas):
    for o in re.split(r"(?<=[.?!])\s+", l):
        if o.strip():
            piezas.append([i, o.strip(), grabar(o.strip())])


def ritmo(p) -> float:
    """Segundos por carácter, descontando un margen fijo por oración."""
    return max(len(p[2]) / 2 / sr - 0.25, 0.01) / max(len(p[1]), 1)


largas = [p for p in piezas if len(p[1]) >= 25]
normal = statistics.median(ritmo(p) for p in largas)
regrabadas = 0
for p in largas:
    intentos = 0
    while ritmo(p) > normal * LIMITE and intentos < REINTENTOS:
        nuevo = grabar(p[1])
        if len(nuevo) < len(p[2]):
            p[2] = nuevo
        intentos += 1
    regrabadas += intentos > 0
peor = max(ritmo(p) / normal for p in largas)

wav = salida.with_suffix(".wav")
out = wave.open(str(wav), "wb")
out.setnchannels(1)
out.setsampwidth(2)
out.setframerate(sr)
silencio = lambda s: b"\x00\x00" * int(sr * s)
for n, p in enumerate(piezas):
    out.writeframes(p[2])
    out.writeframes(silencio(0.35))
    fin_de_linea = n + 1 == len(piezas) or piezas[n + 1][0] != p[0]
    if fin_de_linea:
        # Pausa más larga después de un título de sección (línea corta).
        out.writeframes(silencio(0.9 if len(lineas[p[0]]) < 60 else 0.5))
out.close()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ac", "1", "-b:a", "64k", str(salida)], check=True)
wav.unlink()
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(salida)], capture_output=True, text=True).stdout)
palabras = len(guion.read_text(encoding="utf-8").split())
lineas_hechas = len({p[0] for p in piezas})
print(f"{salida.name}: {lineas_hechas}/{len(lineas)} líneas, {len(piezas)} oraciones, {palabras} palabras, "
      f"{int(dur // 60)}:{int(dur % 60):02d}, regrabadas {regrabadas}, peor ritmo {peor:.2f}x")
