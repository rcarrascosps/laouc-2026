# MCP Server para la agenda del LAOUC Tour 2026

**Fecha:** 2026-06-20
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Contexto y objetivo

El LAOUC Tour 2026 recorre 9 países (Mexico, Guatemala, Costa Rica, Panama, Chile,
Brazil, Uruguay, Argentina, Paraguay). Los speakers preguntan con frecuencia por su
horario, ciudad y detalles de su sesión. El objetivo es exponer la agenda pública del
tour como un servidor MCP remoto, para que los speakers puedan consultarla desde su
propio Claude Desktop/Code sin que el organizador tenga que responder cada pregunta
manualmente.

La fuente de verdad de la agenda (`agenda_laouc_tour_2026.xlsx`, `accepted_sessions.csv`,
`sesiones.xlsx`) sigue viviendo en `C:\rolando\SPS\2026\LAOUC\tour\` y se sigue editando
con Claude Code en ese proyecto. Este proyecto nuevo (`mcp-agenda-server`) es
deliberadamente un repositorio separado para no mezclar el código del servidor con la
carpeta de gestión de speakers, que ya tiene muchos archivos de trabajo.

## Alcance

**Incluye:**
- Script de export que lee la agenda maestra y genera un JSON público filtrado.
- Repositorio Git público en GitHub que aloja ese JSON.
- Servidor MCP remoto (Cloudflare Worker) con 5 herramientas de solo lectura.
- Instrucciones de conexión para que un speaker agregue el servidor a su Claude
  Desktop/Code.

**Explícitamente fuera de alcance (por ahora):**
- Escritura/edición desde el lado del speaker (confirmar asistencia, reportar cambios).
- Autenticación o identificación de quién pregunta — el servidor es de solo lectura
  sobre datos ya públicos, así que no hay datos sensibles que proteger por usuario.
- Exponer emails, notas internas del UG, o estados de Nominated/Waitlisted/Rechazado.

## Arquitectura

```
tour\agenda_laouc_tour_2026.xlsx, sesiones.xlsx   (fuente de verdad, sin tocar)
                  │
                  │  python scripts/export_agenda.py
                  ▼
   mcp-agenda-server\data\agenda-publica.json      (generado, commiteado)
                  │
                  │  git push
                  ▼
        Repo público en GitHub (mismo repo de este proyecto)
                  │
                  │  fetch() en cada consulta (caché ~5 min)
                  ▼
        Cloudflare Worker — servidor MCP (worker\)
                  │
                  │  HTTP / Streamable HTTP transport (protocolo MCP)
                  ▼
   Claude Desktop/Code de cada speaker (custom connector)
```

Tres componentes nuevos, todos dentro de `mcp-agenda-server\`:
1. `scripts/export_agenda.py` — lee desde `tour\` (ruta absoluta) y escribe el JSON público.
2. `data/agenda-publica.json` — el dataset público, versionado en este repo.
3. `worker/` — el código TypeScript del servidor MCP desplegado en Cloudflare Workers.

## Filtro de datos públicos

El export solo incluye sesiones marcadas **VERDE** (aceptadas y confirmadas por el
speaker) en `agenda_laouc_tour_2026.xlsx`. Las sesiones AMARILLAS (pendientes de
confirmación o Nominated/Waitlisted) y ROJAS (rechazadas/separadas) se excluyen del
JSON público — un speaker nunca debe recibir como "definitiva" una sesión que ni
siquiera su dueño ha confirmado.

Campos incluidos por sesión: ciudad, horario, track, si es keynote, título, nombre del
speaker, empresa (tagline), bio corta, y si es Oracle ACE (y de qué nivel). **Nunca**
se incluyen emails ni columnas internas (AcceptedCities crudo, notas del UG, Speaker Id
de Sessionize, etc.).

### Esquema del JSON

```json
{
  "generated_at": "2026-06-20T15:00:00Z",
  "cities": ["Mexico", "Guatemala", "Costa Rica", "Panama", "Chile", "Brazil", "Uruguay", "Argentina", "Paraguay"],
  "sessions": [
    {
      "city": "Mexico",
      "time_slot": "09:00 – 09:45",
      "track": "APEX",
      "is_keynote": true,
      "title": "Usando Inteligencia Artificial CON Oracle AI Database",
      "speaker_name": "Eugenio Galiano",
      "speaker_company": "Oracle",
      "speaker_bio": "...",
      "oracle_ace": null
    }
  ]
}
```

## Servidor MCP

Construido en TypeScript sobre el template oficial de Cloudflare para MCP remoto
(`@modelcontextprotocol/sdk` + Cloudflare Workers, transporte Streamable HTTP).

Herramientas expuestas, todas de solo lectura:

| Herramienta | Qué hace |
|---|---|
| `list_cities` | Lista las 9 ciudades del tour |
| `get_city_agenda(city)` | Agenda completa de una ciudad, ordenada por horario y track |
| `get_speaker_sessions(speaker_name)` | Todas las sesiones de un speaker en cualquier ciudad (coincidencia parcial tolerada) |
| `search_sessions(query)` | Busca por palabra clave en título, track o bio |
| `get_keynotes()` | Lista los keynotes de las 9 ciudades |

Cada llamada del Worker hace `fetch()` al JSON crudo en GitHub (`raw.githubusercontent.com`),
con caché de ~5 minutos en el propio Worker (`caches.default` de Cloudflare) para no
golpear GitHub en cada consulta.

## Flujo de datos de punta a punta

1. Se edita la agenda en `tour\` (como hoy, con Claude Code).
2. Se corre `python scripts/export_agenda.py` desde `mcp-agenda-server\` → regenera
   `data/agenda-publica.json`.
3. `git add data/agenda-publica.json && git commit && git push` al repo público.
4. La siguiente consulta de un speaker llega al Worker con los datos nuevos dentro de
   ~5 minutos (por el caché), sin tocar Cloudflare ni redesplegar nada.
5. El Worker nunca escribe ni modifica los archivos de `tour\` — solo lee el JSON ya
   publicado.

## Manejo de errores

- Si el `fetch()` a GitHub falla o el JSON está mal formado, el Worker devuelve un
  mensaje claro ("La agenda no está disponible en este momento, intenta en unos
  minutos") en vez de fallar silenciosamente o devolver datos parciales.
- Si `get_speaker_sessions` no encuentra coincidencias, devuelve "No encontré sesiones
  para ese nombre" y sugiere revisar la ortografía, en vez de una lista vacía sin
  explicación.
- Si `get_city_agenda` recibe una ciudad fuera de las 9 válidas, devuelve la lista de
  ciudades válidas como ayuda.

## Pruebas

- Local: `wrangler dev` para correr el Worker en local, probado con el MCP Inspector
  (`npx @modelcontextprotocol/inspector`) contra datos reales del JSON antes de cada
  despliegue de código.
- Casos a cubrir: ciudad válida/inválida; nombre de speaker exacto, parcial e
  inexistente; búsqueda con y sin resultados; JSON de GitHub temporalmente
  inaccesible (mock de fetch fallido); nombres compuestos con tildes (ej. "Hector
  Joaquin Andrade Rodriguez", "Iñaqui Medina").
- El script de export también debe poder correr en modo "dry run" para revisar el
  JSON generado antes de hacer commit.

## Distribución a speakers

Una vez desplegado el Worker, se comparte con los speakers (vía el mismo flujo de
correos de `tour\email_manual.md` u otro nuevo) un mini-instructivo con: la URL del
Worker, y los pasos para agregarlo en Claude Desktop/Code como "custom connector"
(Settings → Connectors → Add custom connector → pegar URL). El texto exacto de ese
instructivo se redacta durante la implementación.

## Prerrequisitos

- Cuenta de GitHub (el usuario no tiene una todavía — paso previo a la implementación).
- Cuenta de Cloudflare con Workers habilitado (tampoco existe todavía — paso previo).
- Repo de GitHub público, nuevo, solo para `data/agenda-publica.json` (puede ser el
  mismo repo de este proyecto, ya que todo su contenido es público por diseño).

## Decisiones clave (resumen)

| Decisión | Elegido | Por qué |
|---|---|---|
| Audiencia | Speakers vía MCP remoto | Aceptan la friction de agregar un custom connector una vez |
| Permisos | Solo lectura | Evita conflictos de escritura y validaciones complejas |
| Privacidad | Solo datos públicos de agenda | Nunca expone emails ni notas internas del UG |
| Sincronización | Git como fuente compartida | Cambios casi instantáneos sin redeploy del Worker |
| Hosting | Cloudflare Worker, fetch en vivo | Gratis, serverless, cero mantenimiento |
| Filtro de estado | Solo sesiones VERDES | Nunca se muestra como definitivo algo no confirmado |
| Repo | Público | Simplifica el fetch del Worker, sin secretos que manejar |
| Ubicación del proyecto | Carpeta y repo separados de `tour\` | Mantener el código del MCP server organizado, fuera de la carpeta de gestión de speakers |
