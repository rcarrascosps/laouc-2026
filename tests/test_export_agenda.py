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


def test_parse_session_cell_empty_text_returns_empty_fields():
    assert parse_session_cell('') == {'title': '', 'speaker_name': ''}
    assert parse_session_cell('   \n   ') == {'title': '', 'speaker_name': ''}


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


def _make_sheet_with_lunch_break():
    ws = _make_test_sheet()
    ws['A8'] = '  ALMUERZO  /  LUNCH BREAK     13:00 – 14:30'
    ws.merge_cells('A8:E8')
    return ws


def test_is_keynote_row_false_for_lunch_break_merge():
    ws = _make_sheet_with_lunch_break()
    assert is_keynote_row(ws, 8) is False


def test_extract_city_sessions_produces_no_entry_for_lunch_break_row():
    ws = _make_sheet_with_lunch_break()
    entries = extract_city_sessions(ws)
    assert all(e['time_slot'] != '  ALMUERZO  /  LUNCH BREAK     13:00 – 14:30' for e in entries)
    assert not any(e['is_keynote'] and e['title'].startswith('ALMUERZO') for e in entries)
