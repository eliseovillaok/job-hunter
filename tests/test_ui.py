import pytest

import ui
from ai_engine import ScoredJob
from helpers import make_job


def t(key, **kw):
    return f"[{key}]" + ("" if not kw else str(sorted(kw.items())))


@pytest.mark.parametrize("score,key", [(95, "aff_high"), (80, "aff_high"), (79, "aff_good"), (60, "aff_good"),
                                       (59, "aff_partial"), (40, "aff_partial"), (39, "aff_low"), (0, "aff_low")])
def test_affinity_bands_match_scoring_doc(score, key):
    assert ui.affinity(score)[0] == key


def test_unevaluated_ring_shows_dash_not_score():
    html = ui.ring_html(0, t, evaluated=False)
    assert "—" in html and "[not_evaluated]" in html and ">0<" not in html


def test_job_card_escapes_external_content():
    job = make_job(title="<script>alert(1)</script>", company="Evil & Co <b>", location="<i>x</i>")
    sj = ScoredJob(job=job, score=85, match_reasons=["<img src=x onerror=alert(1)>"],
                   missing_skills=["<b>SQL</b>"], cover_letter=None, summary="<svg onload=1>")
    html = ui.job_card_html(sj, t, chips=["<u>chip</u>"])
    for raw in ("<script>", "<img", "<b>", "<svg onload", "<u>", "<i>x"):
        assert raw not in html
    assert "&lt;script&gt;" in html and "Evil &amp; Co" in html


def test_job_card_unevaluated_hides_reasons():
    sj = ScoredJob(job=make_job(), score=0, match_reasons=["x"], missing_skills=["y"], cover_letter=None,
                   summary="s", evaluated=False)
    html = ui.job_card_html(sj, t, chips=[])
    assert "[not_evaluated_hint]" in html and "✓ x" not in html


def test_avatar_color_is_stable_and_from_palette():
    assert ui.avatar_color("ACME") == ui.avatar_color("acme ")
    assert ui.avatar_color("ACME") in ui._AVATAR_COLORS


def test_stepper_marks_done_current_and_pending():
    html = ui.stepper_html(2, ["a", "b", "c"])
    assert html.count('class="s done"') == 1 and html.count('class="s on"') == 1 and "✓" in html
