# Podcast matutino

Feed privado de un podcast diario de noticias. Una tarea programada genera cada mañana el episodio,
ejecuta `publicar.py` y hace push; Vercel publica la carpeta `public/`.

- `publicar.py`: agrega un episodio y regenera `feed.xml`.
- `config.json`: dirección del sitio, carpeta privada y datos del podcast.
- `episodios.json`: índice de episodios (se conservan los últimos 30).
- `grabar.py`: convierte un guion en MP3 con la voz elegida, controlando el ritmo.
- `publicar_curso.py` y `cursos/`: cursos por entregas, cada uno con su propio feed.
- `registro.json`: noticias ya contadas en los últimos 21 días, para no repetirlas salvo que haya un dato nuevo.
