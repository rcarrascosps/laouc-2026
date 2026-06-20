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
