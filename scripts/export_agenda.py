"""Export the public, confirmed-only LAOUC Tour agenda to JSON for the MCP server."""
import re

GREEN_FILL = 'FFC6EFCE'


def is_confirmed(fill_rgb):
    return fill_rgb == GREEN_FILL


def parse_session_cell(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return {'title': '', 'speaker_name': ''}
    title = lines[0]
    speaker_line = next((l for l in lines[1:] if not l.startswith('(orig')), '')
    speaker_name = re.sub(r'\s*\(KEYNOTE\)\s*', '', speaker_line)
    speaker_name = re.sub(r'\s*\[.*?\]\s*', '', speaker_name).strip()
    return {'title': title, 'speaker_name': speaker_name}


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
