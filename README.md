# Podcast matutino

Feed privado de un podcast diario de noticias. Una tarea programada genera cada mañana el episodio,
ejecuta `publicar.py` y hace push; Vercel publica la carpeta `public/`.

- `publicar.py`: agrega un episodio y regenera `feed.xml`.
- `config.json`: dirección del sitio, carpeta privada y datos del podcast.
- `episodios.json`: índice de episodios (se conservan los últimos 30).
