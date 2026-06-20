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
