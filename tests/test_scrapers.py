import pytest

from scrapers import _clean_desc, matches_keywords


@pytest.mark.parametrize("keywords,text,expected", [
    (["java"], "Senior JavaScript developer", False),
    (["java"], "Java developer", True),
    (["go"], "Google Ads manager", False),
    (["c++"], "Embedded C++ role", True),
    (["node.js"], "node.js backend", True),
    (["contador"], "Contador público", True),
    (["enfermería"], "Licenciada en Enfermería", True),
    (["react native"], "React Native dev", True),
    ([], "anything", True),
    (["  "], "anything", True),
])
def test_matches_keywords_whole_word(keywords, text, expected):
    assert matches_keywords(keywords, text) is expected


def test_clean_desc_strips_html_before_truncating():
    html = "<p>Hola <b>mundo</b> &amp; más</p>" + "<div>x</div>" * 5000
    out = _clean_desc(html)
    assert out.startswith("Hola mundo & más")
    assert "<" not in out and len(out) <= 3000
