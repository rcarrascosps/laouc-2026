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
