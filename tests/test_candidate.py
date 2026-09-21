from candidate import UNKNOWN, CandidateProfile


def test_from_dict_sanitizes_llm_output():
    p = CandidateProfile.from_dict({
        "seniority": "rockstar",            # fuera del enum → unknown
        "years_experience": "no sé",        # no numérico → None
        "skills": [{"name": " Excel ", "evidence": "usa Excel"}, {"name": ""}, "basura"],
        "languages": [{"language": "Inglés", "level": ""}],
        "location": "",
        "search_terms": {"es": ["Contador", " "], "en": ["Accountant"]},
    })
    assert p.seniority == UNKNOWN
    assert p.years_experience is None
    assert [s.name for s in p.skills] == ["Excel"]
    assert p.languages[0].level == UNKNOWN
    assert p.location == UNKNOWN
    assert p.search_terms == {"es": ["Contador"], "en": ["Accountant"]}


def test_negative_years_become_unknown():
    assert CandidateProfile.from_dict({"years_experience": -3}).years_experience is None


def test_roundtrip():
    p = CandidateProfile.from_dict({"summary": "s", "target_roles": ["Chef"], "years_experience": 4,
                                    "skills": [{"name": "Cocina", "evidence": "e"}]})
    assert CandidateProfile.from_dict(p.to_dict()) == p


def test_to_prompt_makes_unknowns_explicit():
    text = CandidateProfile(target_roles=["Electricista"]).to_prompt()
    assert "Seniority: not specified in the CV" in text
    assert "Years of experience: not specified in the CV" in text
    assert "Electricista" in text


def test_all_search_terms_dedupes_case_insensitively():
    p = CandidateProfile(search_terms={"es": ["Enfermero", "UCI"], "en": ["Nurse", "uci"]})
    assert p.all_search_terms() == ["Enfermero", "UCI", "Nurse"]


def test_free_text_profile():
    p = CandidateProfile.from_free_text("  Docente de primaria con 5 años  ")
    assert p.notes == "Docente de primaria con 5 años" and not p.is_empty()
    assert "Additional notes" in p.to_prompt()
