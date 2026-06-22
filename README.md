# LAOUC Tour 2026 — Agenda MCP Server

Servidor MCP de solo lectura con la agenda pública y confirmada del LAOUC Tour 2026,
para que los speakers la consulten desde su propio Claude Desktop o Claude Code.

## Para speakers: cómo conectarte

1. Abre Claude Desktop o Claude Code.
2. Ve a **Settings → Connectors → Add custom connector**.
3. Pega esta URL: `https://laouc-agenda-mcp.rcarrascosps.workers.dev`
4. Guarda y empieza a preguntar, por ejemplo:
   - "¿Cuál es mi sesión en México?"
   - "¿Qué agenda tiene Chile?"
   - "¿Quién da el keynote en Brazil?"

## Para mantenimiento (organizador)

La fuente de verdad de la agenda vive en `C:\rolando\SPS\2026\LAOUC\tour\`. Este repo
nunca la modifica, solo la lee para generar un JSON público.

Después de editar la agenda en `tour\`:

```bash
python scripts/export_agenda.py
git add data/agenda-publica.json
git commit -m "data: actualizar agenda pública"
git push
```

Los cambios quedan visibles para los speakers en unos 5 minutos (por el caché del
Worker), sin necesidad de redesplegar nada.

## Estructura del repo

- `scripts/export_agenda.py` — genera `data/agenda-publica.json` desde la agenda maestra.
- `data/agenda-publica.json` — dataset público (sin emails, solo sesiones confirmadas).
- `worker/` — servidor MCP en Cloudflare Workers (TypeScript).
- `docs/superpowers/specs/` y `docs/superpowers/plans/` — diseño y plan de este proyecto.

## Pruebas

```bash
pytest tests/ -v              # export script
cd worker && npx vitest run   # servidor MCP
```
