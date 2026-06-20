# MCP Agenda Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only remote MCP server that exposes the LAOUC Tour 2026 public agenda (confirmed sessions only) so speakers can query it from their own Claude Desktop/Code.

**Architecture:** A Python export script reads the master agenda (`tour\agenda_laouc_tour_2026.xlsx` + `tour\sesiones.xlsx` + `tour\accepted_sessions.csv`), filters to confirmed (green) sessions only, and writes a public JSON committed to this repo. A Cloudflare Worker implements the MCP server, fetching that JSON live from GitHub's raw content URL on every request (cached ~5 minutes), and exposes 5 read-only tools over the MCP Streamable HTTP transport.

**Tech Stack:** Python 3 (openpyxl, pandas, pytest) for the export script; TypeScript (`@modelcontextprotocol/sdk`, `zod`, `vitest`, `wrangler`) for the Cloudflare Worker.

## Global Constraints

- Read-only: no tool may write to the agenda or any source file.
- Public data only: never expose emails, internal UG notes, raw `AcceptedCities`, or Sessionize internal IDs.
- Only sessions with fill color `FFC6EFCE` (green = confirmed) appear in the public JSON. Yellow/red/white sessions are excluded.
- The export script only **reads** from `C:\rolando\SPS\2026\LAOUC\tour\`. It never modifies any file there.
- This project lives in its own repo at `C:\rolando\SPS\2026\LAOUC\mcp-agenda-server\`, separate from `tour\`.
- Spec: `docs/superpowers/specs/2026-06-20-mcp-agenda-server-design.md` (in this repo).

---

### Task 1: Export script — cell parsing and confirmation filter

**Files:**
- Create: `scripts/export_agenda.py`
- Create: `tests/conftest.py`
- Create: `tests/test_export_agenda.py`
- Create: `requirements.txt`
- Create: `.gitignore`

**Interfaces:**
- Produces: `is_confirmed(fill_rgb: str) -> bool`, `parse_session_cell(text: str) -> dict` (keys: `title: str`, `speaker_name: str`), constant `GREEN_FILL: str = 'FFC6EFCE'` — all in `scripts/export_agenda.py`, consumed by Task 3.

- [ ] **Step 1: Create scaffolding files**

`requirements.txt`:
```
openpyxl
pandas
pytest
```

`.gitignore`:
```
__pycache__/
*.pyc
node_modules/
worker/dist/
.wrangler/
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
```

- [ ] **Step 2: Write the failing tests**

`tests/test_export_agenda.py`:
```python
from export_agenda import is_confirmed, parse_session_cell, GREEN_FILL


def test_is_confirmed_green():
    assert is_confirmed(GREEN_FILL) is True


def test_is_confirmed_yellow_red_white():
    assert is_confirmed('FFFFF2CC') is False
    assert is_confirmed('FFFFC7CE') is False
    assert is_confirmed('FFF5F5F5') is False


def test_parse_session_cell_keynote():
    text = 'Usando Inteligencia Artificial CON Oracle AI Database\nEugenio Galiano  (KEYNOTE)'
    assert parse_session_cell(text) == {
        'title': 'Usando Inteligencia Artificial CON Oracle AI Database',
        'speaker_name': 'Eugenio Galiano',
    }


def test_parse_session_cell_with_orig_tag():
    text = "How to use a relational database for your JSON documents\nPatrick Barel\n(orig: Base de Datos)"
    assert parse_session_cell(text) == {
        'title': 'How to use a relational database for your JSON documents',
        'speaker_name': 'Patrick Barel',
    }


def test_parse_session_cell_with_ace_bracket():
    text = (
        'Real-Time AI: Consolidating Vector Data with OGG 26ai\n'
        'Gilson Martins  [Oracle ACE Director]\n(orig: Base de Datos)'
    )
    assert parse_session_cell(text) == {
        'title': 'Real-Time AI: Consolidating Vector Data with OGG 26ai',
        'speaker_name': 'Gilson Martins',
    }


def test_parse_session_cell_no_speaker_line():
    text = '▶  KEYNOTE  —  PENDIENTE DE CONFIRMAR'
    assert parse_session_cell(text) == {
        'title': '▶  KEYNOTE  —  PENDIENTE DE CONFIRMAR',
        'speaker_name': '',
    }
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_export_agenda.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'export_agenda'`

- [ ] **Step 4: Write the minimal implementation**

`scripts/export_agenda.py`:
```python
"""Export the public, confirmed-only LAOUC Tour agenda to JSON for the MCP server."""
import re

GREEN_FILL = 'FFC6EFCE'


def is_confirmed(fill_rgb):
    return fill_rgb == GREEN_FILL


def parse_session_cell(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    title = lines[0]
    speaker_line = next((l for l in lines[1:] if not l.startswith('(orig')), '')
    speaker_name = re.sub(r'\s*\(KEYNOTE\)\s*', '', speaker_line)
    speaker_name = re.sub(r'\s*\[.*?\]\s*', '', speaker_name).strip()
    return {'title': title, 'speaker_name': speaker_name}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_export_agenda.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/export_agenda.py tests/conftest.py tests/test_export_agenda.py requirements.txt .gitignore
git commit -m "feat: add cell parsing and confirmation filter for agenda export"
```

---

### Task 2: Export script — speaker lookup (tagline/bio enrichment)

**Files:**
- Modify: `scripts/export_agenda.py`
- Modify: `tests/test_export_agenda.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (independent pure functions).
- Produces: `clean_str(value) -> str`, `extract_ace(tagline: str) -> str`, `extract_company(tagline: str) -> str`, `normalize_name(name: str) -> str`, `build_speaker_lookup(accepted_rows: list[dict], orig_rows: list[dict]) -> dict[str, dict]` (each value has keys `company: str`, `bio: str`, `oracle_ace: str`). Consumed by Task 4.
- `accepted_rows` items have keys `FirstName`, `LastName`, `SessionId`. `orig_rows` items have keys `SessionId`, `TagLine`, `Bio`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export_agenda.py`:
```python
from export_agenda import (
    clean_str,
    extract_ace,
    extract_company,
    normalize_name,
    build_speaker_lookup,
)


def test_clean_str_handles_nan_and_none():
    assert clean_str(float('nan')) == ''
    assert clean_str(None) == ''
    assert clean_str('Hello') == 'Hello'


def test_extract_ace_director():
    assert extract_ace('Oracle ACE Director') == 'Oracle ACE Director'


def test_extract_ace_none():
    assert extract_ace('Pythian - Senior Database Consultant') == ''


def test_extract_ace_empty():
    assert extract_ace('') == ''


def test_extract_company_dash_format():
    assert extract_company('Pythian - Senior Database Consultant') == 'Pythian'


def test_extract_company_at_format():
    assert extract_company('Senior Database Consultant at Pythian') == 'Pythian'


def test_normalize_name_collapses_whitespace_and_case():
    assert normalize_name('  Hector Joaquin   Andrade Rodriguez ') == 'hector joaquin andrade rodriguez'


def test_build_speaker_lookup_joins_tagline_and_bio():
    accepted_rows = [
        {'FirstName': 'Eugenio', 'LastName': 'Galiano', 'SessionId': '1152551'},
    ]
    orig_rows = [
        {'SessionId': '1152551', 'TagLine': 'Oracle - Distinguished Product Manager', 'Bio': 'Database expert.'},
    ]
    lookup = build_speaker_lookup(accepted_rows, orig_rows)
    assert lookup['eugenio galiano'] == {
        'company': 'Oracle',
        'bio': 'Database expert.',
        'oracle_ace': '',
    }


def test_build_speaker_lookup_missing_orig_row_yields_empty_fields():
    accepted_rows = [{'FirstName': 'Nobody', 'LastName': 'Here', 'SessionId': '999'}]
    lookup = build_speaker_lookup(accepted_rows, [])
    assert lookup['nobody here'] == {'company': '', 'bio': '', 'oracle_ace': ''}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_export_agenda.py -v`
Expected: FAIL with `ImportError: cannot import name 'clean_str'`

- [ ] **Step 3: Write the minimal implementation**

Append to `scripts/export_agenda.py`:
```python
def clean_str(value):
    if value is None:
        return ''
    if isinstance(value, float) and value != value:  # NaN
        return ''
    return str(value)


def extract_ace(tagline):
    if not tagline:
        return ''
    m = re.search(r'Oracle ACE\s*(Director|Pro|Associate|Apprentice)?', tagline, re.IGNORECASE)
    if not m:
        return ''
    tier = (m.group(1) or '').strip()
    return f'Oracle ACE {tier}'.strip() if tier else 'Oracle ACE'


def extract_company(tagline):
    if not tagline:
        return ''
    tl_clean = re.sub(
        r',?\s*Oracle ACE\s*(?:Director|Pro|Associate|Apprentice)?\s*,?', '', tagline, flags=re.IGNORECASE
    )
    tl_clean = tl_clean.strip().strip(',').strip(' |-').strip()
    if not tl_clean:
        return ''
    if ' - ' in tl_clean:
        return tl_clean.split(' - ')[0].strip()
    m = re.search(r'\bat\s+(.+?)(?:\s*[|,]|$)', tl_clean, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    if ',' in tl_clean:
        first = tl_clean.split(',')[0].strip()
        if len(first.split()) <= 4 and not first[0].islower():
            return first
    if len(tl_clean.split()) <= 3:
        return tl_clean
    return ''


def normalize_name(name):
    return re.sub(r'\s+', ' ', name).strip().casefold()


def build_speaker_lookup(accepted_rows, orig_rows):
    orig_by_id = {r['SessionId']: r for r in orig_rows}
    lookup = {}
    for r in accepted_rows:
        full_name = f"{r['FirstName']} {r['LastName']}".strip()
        key = normalize_name(full_name)
        if key in lookup:
            continue
        orig = orig_by_id.get(r['SessionId'], {})
        tagline = clean_str(orig.get('TagLine'))
        lookup[key] = {
            'company': extract_company(tagline),
            'bio': clean_str(orig.get('Bio')),
            'oracle_ace': extract_ace(tagline),
        }
    return lookup
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_export_agenda.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 5: Commit**

```bash
git add scripts/export_agenda.py tests/test_export_agenda.py
git commit -m "feat: add speaker tagline/bio lookup for agenda export"
```

---

### Task 3: Export script — per-sheet session extraction

**Files:**
- Modify: `scripts/export_agenda.py`
- Modify: `tests/test_export_agenda.py`

**Interfaces:**
- Consumes: `parse_session_cell` from Task 1.
- Produces: `is_keynote_row(ws, row_idx: int) -> bool`, `extract_city_sessions(ws) -> list[dict]` (each dict has keys `city`, `time_slot`, `track`, `is_keynote`, `title`, `speaker_name`, `fill_rgb`). Consumed by Task 4.
- `ws` is an `openpyxl.worksheet.worksheet.Worksheet` whose `.title` is the city name, row 2 holds track headers in columns B–E, row 3 is the keynote row (merged B3:E3), and session cells start at row 3.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export_agenda.py`:
```python
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from export_agenda import is_keynote_row, extract_city_sessions


def _make_test_sheet():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Mexico'
    ws['A2'] = 'Horario'
    ws['B2'] = 'APEX'
    ws['C2'] = 'Base de Datos'
    ws['D2'] = 'Cloud & Diff. Topics'
    ws['E2'] = 'Inteligencia Artificial'
    ws.merge_cells('B3:E3')
    ws['B3'] = 'Keynote Title\nKeynote Speaker  (KEYNOTE)'
    ws['A4'] = '09:45 – 10:30'
    ws['B4'] = 'APEX Session\nSpeaker One'
    return ws


def test_is_keynote_row_true_for_merged_row():
    assert is_keynote_row(_make_test_sheet(), 3) is True


def test_is_keynote_row_false_for_normal_row():
    assert is_keynote_row(_make_test_sheet(), 4) is False


def test_extract_city_sessions_reads_keynote_and_track_session():
    ws = _make_test_sheet()
    green = PatternFill(start_color='FFC6EFCE', end_color='FFC6EFCE', fill_type='solid')
    ws['B3'].fill = green
    ws['B4'].fill = green

    entries = extract_city_sessions(ws)

    assert entries == [
        {
            'city': 'Mexico', 'time_slot': None, 'track': None, 'is_keynote': True,
            'title': 'Keynote Title', 'speaker_name': 'Keynote Speaker', 'fill_rgb': 'FFC6EFCE',
        },
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'APEX Session', 'speaker_name': 'Speaker One', 'fill_rgb': 'FFC6EFCE',
        },
    ]


def test_extract_city_sessions_skips_empty_cells():
    ws = _make_test_sheet()
    ws['B3'] = None
    entries = extract_city_sessions(ws)
    assert entries == [
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'APEX Session', 'speaker_name': 'Speaker One', 'fill_rgb': '00000000',
        },
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_export_agenda.py -v`
Expected: FAIL with `ImportError: cannot import name 'is_keynote_row'`

- [ ] **Step 3: Write the minimal implementation**

Append to `scripts/export_agenda.py`:
```python
def is_keynote_row(ws, row_idx):
    for rng in ws.merged_cells.ranges:
        if rng.min_row == row_idx and rng.min_col == 2 and rng.max_col == 5:
            return True
    return False


def extract_city_sessions(ws):
    city = ws.title
    track_names = {col: ws.cell(row=2, column=col).value for col in range(2, 6)}
    entries = []
    for row in range(3, ws.max_row + 1):
        time_slot = ws.cell(row=row, column=1).value
        keynote = is_keynote_row(ws, row)
        for col in range(2, 6):
            cell = ws.cell(row=row, column=col)
            if not cell.value:
                continue
            parsed = parse_session_cell(cell.value)
            entries.append({
                'city': city,
                'time_slot': None if keynote else time_slot,
                'track': None if keynote else track_names[col],
                'is_keynote': keynote,
                'title': parsed['title'],
                'speaker_name': parsed['speaker_name'],
                'fill_rgb': cell.fill.fgColor.rgb,
            })
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_export_agenda.py -v`
Expected: PASS (16 tests total)

- [ ] **Step 5: Commit**

```bash
git add scripts/export_agenda.py tests/test_export_agenda.py
git commit -m "feat: add per-sheet session extraction for agenda export"
```

---

### Task 4: Export script — orchestration, filtering, and JSON output

**Files:**
- Modify: `scripts/export_agenda.py`
- Modify: `tests/test_export_agenda.py`

**Interfaces:**
- Consumes: `is_confirmed`, `GREEN_FILL` (Task 1); `normalize_name`, `build_speaker_lookup` (Task 2); `extract_city_sessions` (Task 3).
- Produces: `build_public_sessions(raw_entries: list[dict], speaker_lookup: dict[str, dict]) -> list[dict]`, `main() -> None`. `main()` writes `data/agenda-publica.json` relative to the repo root.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_agenda.py`:
```python
from export_agenda import build_public_sessions


def test_build_public_sessions_filters_unconfirmed_and_enriches():
    raw_entries = [
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'APEX Session', 'speaker_name': 'Eugenio Galiano', 'fill_rgb': 'FFC6EFCE',
        },
        {
            'city': 'Mexico', 'time_slot': '10:30 – 11:15', 'track': 'APEX', 'is_keynote': False,
            'title': 'Unconfirmed Session', 'speaker_name': 'Someone Pending', 'fill_rgb': 'FFFFF2CC',
        },
    ]
    speaker_lookup = {
        'eugenio galiano': {'company': 'Oracle', 'bio': 'Bio text.', 'oracle_ace': ''},
    }

    result = build_public_sessions(raw_entries, speaker_lookup)

    assert result == [
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'APEX Session', 'speaker_name': 'Eugenio Galiano',
            'speaker_company': 'Oracle', 'speaker_bio': 'Bio text.', 'oracle_ace': None,
        },
    ]


def test_build_public_sessions_unmatched_speaker_gets_empty_enrichment():
    raw_entries = [
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'Mystery Session', 'speaker_name': 'Unknown Person', 'fill_rgb': 'FFC6EFCE',
        },
    ]
    result = build_public_sessions(raw_entries, {})
    assert result == [
        {
            'city': 'Mexico', 'time_slot': '09:45 – 10:30', 'track': 'APEX', 'is_keynote': False,
            'title': 'Mystery Session', 'speaker_name': 'Unknown Person',
            'speaker_company': '', 'speaker_bio': '', 'oracle_ace': None,
        },
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_agenda.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_public_sessions'`

- [ ] **Step 3: Write the minimal implementation**

Append to `scripts/export_agenda.py`:
```python
def build_public_sessions(raw_entries, speaker_lookup):
    public_sessions = []
    for entry in raw_entries:
        if not is_confirmed(entry['fill_rgb']):
            continue
        info = speaker_lookup.get(normalize_name(entry['speaker_name']), {})
        public_sessions.append({
            'city': entry['city'],
            'time_slot': entry['time_slot'],
            'track': entry['track'],
            'is_keynote': entry['is_keynote'],
            'title': entry['title'],
            'speaker_name': entry['speaker_name'],
            'speaker_company': info.get('company', ''),
            'speaker_bio': info.get('bio', ''),
            'oracle_ace': info.get('oracle_ace', '') or None,
        })
    return public_sessions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_export_agenda.py -v`
Expected: PASS (18 tests total)

- [ ] **Step 5: Add the `main()` orchestration (no new unit test — wires real I/O)**

Append to `scripts/export_agenda.py`:
```python
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

TOUR_DIR = Path(r"C:\rolando\SPS\2026\LAOUC\tour")
AGENDA_XLSX = TOUR_DIR / "agenda_laouc_tour_2026.xlsx"
SESIONES_XLSX = TOUR_DIR / "sesiones.xlsx"
ACCEPTED_CSV = TOUR_DIR / "accepted_sessions.csv"
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "data" / "agenda-publica.json"

CITIES = ['Mexico', 'Guatemala', 'Costa Rica', 'Panama', 'Chile',
          'Brazil', 'Uruguay', 'Argentina', 'Paraguay']


def main():
    accepted = pd.read_csv(ACCEPTED_CSV, dtype={'SessionId': str}).to_dict('records')
    orig_df = pd.read_excel(
        SESIONES_XLSX, sheet_name='Sessions and speakers - Origina', dtype={'Session Id': str}
    )
    orig_df = orig_df.rename(columns={'Session Id': 'SessionId'})
    orig_rows = orig_df.to_dict('records')

    speaker_lookup = build_speaker_lookup(accepted, orig_rows)

    wb = load_workbook(AGENDA_XLSX)
    all_public_sessions = []
    for city in CITIES:
        ws = wb[city]
        raw_entries = extract_city_sessions(ws)
        all_public_sessions.extend(build_public_sessions(raw_entries, speaker_lookup))

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'cities': CITIES,
        'sessions': all_public_sessions,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(all_public_sessions)} sessions -> {OUTPUT_JSON}')


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS (18 tests — `main()` has no unit test, it is exercised in Step 7)

- [ ] **Step 7: Run the script against the real tour data and inspect the output**

Run: `python scripts/export_agenda.py`
Expected output: `Wrote N sessions -> ...\data\agenda-publica.json` where N is roughly the count of green-filled sessions across all 9 city sheets (expect well over 100 once every city has been worked through; far fewer today since only Mexico has been fully colored).

Open `data/agenda-publica.json` and confirm: every Mexico session you already confirmed (Eugenio Galiano's keynote, Jayson Hanes, etc.) appears with `speaker_company`/`speaker_bio` populated, and none of the speakers still in amarillo (Paulo Künzel, Matheus Boesing, Guilherme Brito, Rita Nunez) appear for Mexico.

- [ ] **Step 8: Commit**

```bash
git add scripts/export_agenda.py tests/test_export_agenda.py data/agenda-publica.json
git commit -m "feat: orchestrate full agenda export to public JSON"
```

---

### Task 5: Worker scaffold and data fetch/cache module

**Files:**
- Create: `worker/package.json`
- Create: `worker/tsconfig.json`
- Create: `worker/wrangler.toml`
- Create: `worker/src/data.ts`
- Create: `worker/test/data.test.ts`

**Interfaces:**
- Produces: `interface PublicSession`, `interface AgendaData`, `class AgendaFetchError extends Error`, `async function fetchAgendaData(agendaJsonUrl: string): Promise<AgendaData>` — all in `worker/src/data.ts`. Consumed by Tasks 6 and 7.

- [ ] **Step 1: Create the worker scaffold**

`worker/package.json`:
```json
{
  "name": "laouc-agenda-mcp-worker",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "test": "vitest run"
  },
  "devDependencies": {
    "@cloudflare/workers-types": "^4.20250101.0",
    "typescript": "^5.5.4",
    "vitest": "^2.1.4",
    "wrangler": "^3.99.0"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.9.0",
    "zod": "^3.23.8"
  }
}
```

`worker/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "Bundler",
    "lib": ["ES2022"],
    "types": ["@cloudflare/workers-types"],
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true
  },
  "include": ["src", "test"]
}
```

`worker/wrangler.toml` (replace `<github-user>` with the real GitHub username once the repo exists in Task 9):
```toml
name = "laouc-agenda-mcp"
main = "src/index.ts"
compatibility_date = "2025-01-01"

[vars]
AGENDA_JSON_URL = "https://raw.githubusercontent.com/<github-user>/mcp-agenda-server/master/data/agenda-publica.json"
```

Run: `cd worker && npm install`
Expected: dependencies installed, `worker/node_modules` created.

- [ ] **Step 2: Write the failing tests**

`worker/test/data.test.ts`:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchAgendaData, AgendaFetchError } from '../src/data';

const SAMPLE_DATA = {
  generated_at: '2026-06-20T00:00:00Z',
  cities: ['Mexico'],
  sessions: [],
};

function installFakeCache() {
  const store = new Map<string, Response>();
  // @ts-expect-error - simplified Cache mock for tests, real shape not needed
  globalThis.caches = {
    default: {
      async match(req: Request) {
        return store.get(req.url);
      },
      async put(req: Request, res: Response) {
        store.set(req.url, res);
      },
    },
  };
}

describe('fetchAgendaData', () => {
  beforeEach(() => {
    installFakeCache();
  });

  it('returns parsed JSON on a successful fetch', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE_DATA), { status: 200 }));

    const result = await fetchAgendaData('https://example.com/agenda.json');

    expect(result).toEqual(SAMPLE_DATA);
  });

  it('serves the second call from cache without calling fetch again', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE_DATA), { status: 200 }));
    globalThis.fetch = fetchMock;

    await fetchAgendaData('https://example.com/agenda.json');
    await fetchAgendaData('https://example.com/agenda.json');

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws AgendaFetchError when the network request fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });

  it('throws AgendaFetchError on a non-200 response', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('not found', { status: 404 }));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });

  it('throws AgendaFetchError when the body is not valid JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('not json', { status: 200 }));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd worker && npx vitest run test/data.test.ts`
Expected: FAIL — `Cannot find module '../src/data'`

- [ ] **Step 4: Write the minimal implementation**

`worker/src/data.ts`:
```typescript
export interface PublicSession {
  city: string;
  time_slot: string | null;
  track: string | null;
  is_keynote: boolean;
  title: string;
  speaker_name: string;
  speaker_company: string;
  speaker_bio: string;
  oracle_ace: string | null;
}

export interface AgendaData {
  generated_at: string;
  cities: string[];
  sessions: PublicSession[];
}

export class AgendaFetchError extends Error {}

const CACHE_KEY = 'https://laouc-agenda-mcp.internal/agenda-cache';
const CACHE_TTL_SECONDS = 300;

export async function fetchAgendaData(agendaJsonUrl: string): Promise<AgendaData> {
  const cache = caches.default;
  const cacheRequest = new Request(CACHE_KEY);

  const cached = await cache.match(cacheRequest);
  if (cached) {
    return (await cached.json()) as AgendaData;
  }

  let response: Response;
  try {
    response = await fetch(agendaJsonUrl);
  } catch (err) {
    throw new AgendaFetchError(`No se pudo contactar a GitHub: ${(err as Error).message}`);
  }

  if (!response.ok) {
    throw new AgendaFetchError(`GitHub respondió con estado ${response.status}`);
  }

  let data: AgendaData;
  try {
    data = (await response.json()) as AgendaData;
  } catch (err) {
    throw new AgendaFetchError('El JSON de la agenda está mal formado.');
  }

  const cacheResponse = new Response(JSON.stringify(data), {
    headers: { 'Cache-Control': `max-age=${CACHE_TTL_SECONDS}` },
  });
  await cache.put(cacheRequest, cacheResponse);

  return data;
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd worker && npx vitest run test/data.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add worker/package.json worker/tsconfig.json worker/wrangler.toml worker/src/data.ts worker/test/data.test.ts
git commit -m "feat: add worker scaffold and cached agenda data fetcher"
```

---

### Task 6: Worker query tools

**Files:**
- Create: `worker/src/tools.ts`
- Create: `worker/test/tools.test.ts`

**Interfaces:**
- Consumes: `AgendaData`, `PublicSession` from `worker/src/data.ts` (Task 5).
- Produces: `listCities(data: AgendaData): string[]`, `getCityAgenda(data: AgendaData, city: string): PublicSession[] | { error: string; valid_cities: string[] }`, `getSpeakerSessions(data: AgendaData, speakerName: string): PublicSession[]`, `searchSessions(data: AgendaData, query: string): PublicSession[]`, `getKeynotes(data: AgendaData): PublicSession[]` — all in `worker/src/tools.ts`. Consumed by Task 7.

- [ ] **Step 1: Write the failing tests**

`worker/test/tools.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { listCities, getCityAgenda, getSpeakerSessions, searchSessions, getKeynotes } from '../src/tools';
import type { AgendaData } from '../src/data';

const DATA: AgendaData = {
  generated_at: '2026-06-20T00:00:00Z',
  cities: ['Mexico', 'Chile'],
  sessions: [
    {
      city: 'Mexico', time_slot: null, track: null, is_keynote: true,
      title: 'Keynote MX', speaker_name: 'Eugenio Galiano', speaker_company: 'Oracle',
      speaker_bio: 'AI expert.', oracle_ace: null,
    },
    {
      city: 'Mexico', time_slot: '09:45 – 10:30', track: 'APEX', is_keynote: false,
      title: 'APEX Talk', speaker_name: 'Jayson Hanes', speaker_company: 'Oracle',
      speaker_bio: 'APEX product manager.', oracle_ace: null,
    },
    {
      city: 'Chile', time_slot: null, track: null, is_keynote: true,
      title: 'Keynote CL', speaker_name: 'Eugenio Galiano', speaker_company: 'Oracle',
      speaker_bio: 'AI expert.', oracle_ace: null,
    },
  ],
};

describe('listCities', () => {
  it('returns the cities list', () => {
    expect(listCities(DATA)).toEqual(['Mexico', 'Chile']);
  });
});

describe('getCityAgenda', () => {
  it('returns sessions for a valid city sorted by time slot', () => {
    expect(getCityAgenda(DATA, 'Mexico')).toEqual([DATA.sessions[0], DATA.sessions[1]]);
  });

  it('returns an error with valid cities for an unknown city', () => {
    expect(getCityAgenda(DATA, 'Atlantis')).toEqual({
      error: 'Ciudad no encontrada: Atlantis',
      valid_cities: ['Mexico', 'Chile'],
    });
  });
});

describe('getSpeakerSessions', () => {
  it('finds sessions by exact name across cities', () => {
    expect(getSpeakerSessions(DATA, 'Eugenio Galiano')).toEqual([DATA.sessions[0], DATA.sessions[2]]);
  });

  it('finds sessions by partial, case-insensitive name', () => {
    expect(getSpeakerSessions(DATA, 'galiano')).toHaveLength(2);
  });

  it('returns an empty array for an unknown speaker', () => {
    expect(getSpeakerSessions(DATA, 'Nobody Here')).toEqual([]);
  });
});

describe('searchSessions', () => {
  it('matches by title keyword', () => {
    expect(searchSessions(DATA, 'APEX')).toEqual([DATA.sessions[1]]);
  });

  it('returns an empty array when nothing matches', () => {
    expect(searchSessions(DATA, 'nonexistent-topic')).toEqual([]);
  });
});

describe('getKeynotes', () => {
  it('returns only keynote sessions across all cities', () => {
    expect(getKeynotes(DATA)).toEqual([DATA.sessions[0], DATA.sessions[2]]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd worker && npx vitest run test/tools.test.ts`
Expected: FAIL — `Cannot find module '../src/tools'`

- [ ] **Step 3: Write the minimal implementation**

`worker/src/tools.ts`:
```typescript
import type { AgendaData, PublicSession } from './data';

export function listCities(data: AgendaData): string[] {
  return data.cities;
}

export function getCityAgenda(
  data: AgendaData,
  city: string
): PublicSession[] | { error: string; valid_cities: string[] } {
  if (!data.cities.includes(city)) {
    return { error: `Ciudad no encontrada: ${city}`, valid_cities: data.cities };
  }
  return data.sessions
    .filter((s) => s.city === city)
    .sort((a, b) => (a.time_slot ?? '').localeCompare(b.time_slot ?? ''));
}

function normalize(text: string): string {
  return text.trim().toLowerCase();
}

export function getSpeakerSessions(data: AgendaData, speakerName: string): PublicSession[] {
  const needle = normalize(speakerName);
  return data.sessions.filter((s) => normalize(s.speaker_name).includes(needle));
}

export function searchSessions(data: AgendaData, query: string): PublicSession[] {
  const needle = normalize(query);
  return data.sessions.filter(
    (s) =>
      normalize(s.title).includes(needle) ||
      normalize(s.track ?? '').includes(needle) ||
      normalize(s.speaker_bio).includes(needle)
  );
}

export function getKeynotes(data: AgendaData): PublicSession[] {
  return data.sessions.filter((s) => s.is_keynote);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd worker && npx vitest run test/tools.test.ts`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add worker/src/tools.ts worker/test/tools.test.ts
git commit -m "feat: add agenda query tools (cities, speaker, search, keynotes)"
```

---

### Task 7: Wire the MCP server (index.ts)

**Files:**
- Create: `worker/src/index.ts`

**Interfaces:**
- Consumes: `fetchAgendaData`, `AgendaFetchError` (Task 5); `listCities`, `getCityAgenda`, `getSpeakerSessions`, `searchSessions`, `getKeynotes` (Task 6).
- Produces: default-exported Workers `fetch` handler, used directly by `wrangler dev`/`wrangler deploy` — no other task consumes this module.

This task wires together already-tested logic; the wiring itself is verified manually in Task 8 with the MCP Inspector rather than with vitest, since it is thin glue code with no independent branches of its own.

- [ ] **Step 1: Confirm the current MCP SDK transport API before wiring**

The `@modelcontextprotocol/sdk` Workers integration (`McpServer` + `StreamableHTTPServerTransport`) evolves between versions. Before writing `index.ts`, run:

```bash
cd worker && npm view @modelcontextprotocol/sdk versions --json
```

and check the installed version's `server/mcp.js` and `server/streamableHttp.js` exports (`node -e "console.log(Object.keys(require('@modelcontextprotocol/sdk/server/mcp.js')))"` or read `node_modules/@modelcontextprotocol/sdk/dist/esm/server/streamableHttp.d.ts`). The code below targets the `McpServer.tool(name, description, schema, handler)` + `StreamableHTTPServerTransport` shape current as of SDK 1.9.x. If the installed version's API differs, adapt the registration calls and the `fetch` handler accordingly — the test suite in Tasks 5–6 is unaffected either way since it covers `data.ts`/`tools.ts` directly.

- [ ] **Step 2: Write index.ts**

`worker/src/index.ts`:
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';
import { fetchAgendaData, AgendaFetchError } from './data';
import { listCities, getCityAgenda, getSpeakerSessions, searchSessions, getKeynotes } from './tools';

export interface Env {
  AGENDA_JSON_URL: string;
}

function buildServer(env: Env): McpServer {
  const server = new McpServer({ name: 'laouc-agenda', version: '1.0.0' });

  server.tool('list_cities', 'Lista las 9 ciudades del LAOUC Tour 2026', {}, async () => {
    const data = await fetchAgendaData(env.AGENDA_JSON_URL);
    return { content: [{ type: 'text', text: JSON.stringify(listCities(data)) }] };
  });

  server.tool(
    'get_city_agenda',
    'Devuelve la agenda completa de una ciudad del tour, ordenada por horario',
    { city: z.string().describe('Nombre exacto de la ciudad, ej. "Mexico"') },
    async ({ city }: { city: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      return { content: [{ type: 'text', text: JSON.stringify(getCityAgenda(data, city)) }] };
    }
  );

  server.tool(
    'get_speaker_sessions',
    'Devuelve todas las sesiones confirmadas de un speaker en cualquier ciudad del tour',
    { speaker_name: z.string().describe('Nombre completo o parcial del speaker') },
    async ({ speaker_name }: { speaker_name: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      const sessions = getSpeakerSessions(data, speaker_name);
      const text = sessions.length
        ? JSON.stringify(sessions)
        : `No encontré sesiones para "${speaker_name}". Revisa la ortografía del nombre.`;
      return { content: [{ type: 'text', text }] };
    }
  );

  server.tool(
    'search_sessions',
    'Busca sesiones por palabra clave en el título, track o biografía del speaker',
    { query: z.string().describe('Palabra clave a buscar, ej. "AI" o "GoldenGate"') },
    async ({ query }: { query: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      const sessions = searchSessions(data, query);
      const text = sessions.length
        ? JSON.stringify(sessions)
        : `No encontré sesiones que coincidan con "${query}".`;
      return { content: [{ type: 'text', text }] };
    }
  );

  server.tool('get_keynotes', 'Lista los keynotes confirmados de las 9 ciudades del tour', {}, async () => {
    const data = await fetchAgendaData(env.AGENDA_JSON_URL);
    return { content: [{ type: 'text', text: JSON.stringify(getKeynotes(data)) }] };
  });

  return server;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      const server = buildServer(env);
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      await server.connect(transport);
      return await transport.handleRequest(request);
    } catch (err) {
      if (err instanceof AgendaFetchError) {
        return new Response(
          JSON.stringify({ error: `La agenda no está disponible en este momento: ${err.message}` }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(JSON.stringify({ error: 'Error interno del servidor.' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
```

- [ ] **Step 3: Type-check**

Run: `cd worker && npx tsc --noEmit`
Expected: no errors. If `transport.handleRequest` or the constructor signature differs from the installed SDK version (per Step 1's check), fix the call here until this passes — that is the actual contract this task must satisfy, not the literal code above.

- [ ] **Step 4: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: wire MCP server with the 5 agenda tools"
```

---

### Task 8: Local end-to-end verification with MCP Inspector

**Files:** none (manual verification task)

- [ ] **Step 1: Generate a small local test JSON**

Run (from the repo root, with Task 4's script already run at least once):
```bash
ls data/agenda-publica.json
```
Expected: file exists with real Mexico sessions.

- [ ] **Step 2: Start the worker locally**

```bash
cd worker
npx wrangler dev
```
Expected: console prints a local URL, e.g. `http://localhost:8787`.

- [ ] **Step 3: Run the MCP Inspector against it**

In a second terminal:
```bash
npx @modelcontextprotocol/inspector
```
Open the printed Inspector URL in a browser, connect it to `http://localhost:8787` using the Streamable HTTP transport, and call each of the 5 tools:
- `list_cities` → expect the 9-city array.
- `get_city_agenda` with `city="Mexico"` → expect the confirmed Mexico sessions (Eugenio Galiano's keynote, Jayson Hanes, etc.), sorted by time.
- `get_city_agenda` with `city="Atlantis"` → expect the `{error, valid_cities}` shape.
- `get_speaker_sessions` with `speaker_name="Galiano"` → expect his sessions.
- `get_speaker_sessions` with `speaker_name="Nobody"` → expect the "No encontré sesiones..." message.
- `search_sessions` with `query="AI"` → expect multiple matches.
- `get_keynotes` → expect at least the Mexico keynote.

- [ ] **Step 4: Verify the error path**

Temporarily set `AGENDA_JSON_URL` in `worker/wrangler.toml` to an invalid URL (e.g. add a typo), restart `wrangler dev`, call any tool, and confirm the response is the 503 with the "La agenda no está disponible..." message rather than an unhandled exception. Revert the URL afterward.

- [ ] **Step 5: Record the result**

No commit needed for this task — it is a verification checkpoint. If any tool misbehaves, fix the relevant file from Task 6/7 and re-run this task before moving on.

---

### Task 9: Create accounts, push the repo, and deploy

**Files:** none (account setup and deployment; manual steps requiring the user's own credentials)

- [ ] **Step 1: Create a GitHub account and repository (user action)**

If you don't already have a GitHub account, create one at https://github.com/signup. Then create a new **public** repository named `mcp-agenda-server` (no README/license, since this local repo already has content).

- [ ] **Step 2: Push this repo to GitHub**

```bash
cd "C:\rolando\SPS\2026\LAOUC\mcp-agenda-server"
git remote add origin https://github.com/<your-github-username>/mcp-agenda-server.git
git branch -M master
git push -u origin master
```

- [ ] **Step 3: Update wrangler.toml with the real raw URL**

Edit `worker/wrangler.toml`, replacing `<github-user>` with `<your-github-username>` from Step 1, and commit:
```bash
git add worker/wrangler.toml
git commit -m "chore: point worker at the real GitHub raw URL"
git push
```

- [ ] **Step 4: Create a Cloudflare account (user action)**

If you don't already have one, create a free account at https://dash.cloudflare.com/sign-up and enable Workers (Cloudflare prompts for this on first Workers visit).

- [ ] **Step 5: Authenticate wrangler and deploy**

```bash
cd worker
npx wrangler login
npx wrangler deploy
```
Expected: output ends with a line like `Published laouc-agenda-mcp ... https://laouc-agenda-mcp.<your-subdomain>.workers.dev`. Save that URL — it is what speakers will connect to.

- [ ] **Step 6: Smoke-test the deployed worker**

Repeat Task 8 Step 3's Inspector checks against the deployed URL instead of `localhost:8787`.

---

### Task 10: Speaker-facing README and final commit

**Files:**
- Create: `README.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Write the README**

`README.md`:
```markdown
# LAOUC Tour 2026 — Agenda MCP Server

Servidor MCP de solo lectura con la agenda pública y confirmada del LAOUC Tour 2026,
para que los speakers la consulten desde su propio Claude Desktop o Claude Code.

## Para speakers: cómo conectarte

1. Abre Claude Desktop o Claude Code.
2. Ve a **Settings → Connectors → Add custom connector**.
3. Pega esta URL: `https://laouc-agenda-mcp.<tu-subdominio>.workers.dev`
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add speaker connection instructions and maintenance guide"
git push
```

---

## Self-Review Notes

- **Spec coverage:** export script (filter + enrichment) → Tasks 1–4; 5 MCP tools → Tasks 5–7; error handling → Tasks 5, 7, 8 Step 4; testing → every task's own test steps plus Task 8; distribution to speakers → Task 10. Hosting/account prerequisites → Task 9.
- **Type consistency:** `PublicSession`/`AgendaData` defined once in `worker/src/data.ts` (Task 5) and imported, never redefined, in `worker/src/tools.ts` (Task 6) and `worker/src/index.ts` (Task 7). Python dict shapes from `extract_city_sessions` (Task 3) match exactly what `build_public_sessions` (Task 4) consumes (`city`, `time_slot`, `track`, `is_keynote`, `title`, `speaker_name`, `fill_rgb`).
- **Known risk flagged explicitly:** Task 7's exact `@modelcontextprotocol/sdk` wiring (`McpServer`/`StreamableHTTPServerTransport` API) may drift from what's written here by the time this is implemented; Task 7 Step 1 requires checking the installed version before treating the provided code as final.
