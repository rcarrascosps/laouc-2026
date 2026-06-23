# LAOUC Tour 2026 — Agenda MCP Server

A read-only MCP server with the public, confirmed agenda for the LAOUC Tour 2026.
Speakers and country coordinators can connect it to their own Claude Desktop or
Claude Code and ask questions about the agenda in natural language — no login,
spreadsheet, or API key required.

**Server URL:** `https://laouc-agenda-mcp.rcarrascosps.workers.dev`

## How to connect (Claude Desktop)

1. Open **Claude Desktop**.
2. Go to **Settings → Connectors**.
3. Click **Add custom connector** (bottom of the "Custom connectors" section).
4. Set **Name** to `LAOUC Agenda 2026`.
5. Set **URL** to `https://laouc-agenda-mcp.rcarrascosps.workers.dev`.
6. Save. Claude should detect the server and list 5 available tools.
7. Start a new chat and ask away.

## How to connect (Claude Code)

```
claude mcp add --transport http laouc-agenda https://laouc-agenda-mcp.rcarrascosps.workers.dev
```

## Other MCP clients

This isn't a Claude-only server — it's a standard MCP server using the
[Streamable HTTP transport](https://modelcontextprotocol.io/), with no auth required.
Any MCP client that supports remote HTTP servers can connect using the same URL:
Claude.ai (web), Cursor, Windsurf, and other MCP-compatible agents/IDEs. Check your
client's docs for how it registers a remote MCP server — the URL is the only thing
you need: `https://laouc-agenda-mcp.rcarrascosps.workers.dev`.

Clients that only support local (stdio) MCP servers won't be able to connect directly.

## What you can ask

- "What's the agenda for Chile?"
- "Who's speaking in Brazil?"
- "Find my sessions" (mention your name)
- "Who's giving the keynote in Mexico?"
- "Search for sessions about GoldenGate"
- "What date is the Mexico stop?"

## Available tools

| Tool | What it does |
|------|---------------|
| `list_cities` | Lists the 9 tour cities, each with its event date |
| `get_city_agenda` | Full agenda for one city — date, local time slot, track — sorted by time slot |
| `get_speaker_sessions` | All confirmed sessions for a given speaker, across cities |
| `search_sessions` | Keyword search across session title, track, and speaker bio |
| `get_keynotes` | Confirmed keynotes for all 9 cities |

Every session includes a `date` field (ISO `YYYY-MM-DD`) for its city's tour stop, plus
`time_slot`. **`time_slot` is always the local agenda time of that session's own city —
it is never adjusted for timezone.** If you're looking at a speaker's sessions across
multiple cities, each `time_slot` belongs to a different local clock, not a shared one.

The data only includes confirmed sessions (green/accepted) and contains no emails or
other personal contact info — it's safe to share this URL publicly with speakers.

## Maintenance (organizer only)

The source of truth for the agenda lives in `C:\rolando\SPS\2026\LAOUC\tour\`. This
repo never modifies it — it only reads it to generate a public JSON snapshot.

After editing the agenda in `tour\`:

```bash
python scripts/export_agenda.py
git add data/agenda-publica.json
git commit -m "data: update public agenda"
git push
```

Changes become visible to speakers within ~5 minutes (Worker cache), no redeploy
needed.

Per-city event dates live in `CITY_DATES` at the top of `scripts/export_agenda.py` —
they're organizer-confirmed and don't come from the spreadsheet. If a city's date
changes, edit that dict and re-run the export.

### Repo structure

- `scripts/export_agenda.py` — generates `data/agenda-publica.json` from the master agenda.
- `data/agenda-publica.json` — public dataset (confirmed sessions only, no emails).
- `worker/` — MCP server on Cloudflare Workers (TypeScript).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — design and plan for this project.

### Tests

```bash
pytest tests/ -v              # export script
cd worker && npx vitest run   # MCP server
```
