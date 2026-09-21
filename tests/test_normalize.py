import pytest

import normalize
from helpers import make_job


@pytest.mark.parametrize("text,expected", [
    ("Buscamos una persona con experiencia para el equipo de la empresa, que trabaje con nosotros", "es"),
    ("We are looking for someone with experience to join our team and work with you", "en"),
    ("Wir suchen für unser Unternehmen eine Person mit Erfahrung und die Sie", "de"),
    # Avisos cortos también se detectan.
    ("Contador recibido con hasta 2 años de experiencia. Presencial.", "es"),
    ("Close deals. 3+ years of B2B experience required.", "en"),
    ("Atendimento por e-mail e chat. Português fluente obrigatório.", "pt"),
    ("Java Python SQL", "unknown"),
    ("", "unknown"),
])
def test_detect_language(text, expected):
    assert normalize.detect_language(text) == expected


@pytest.mark.parametrize("title,expected", [
    ("Senior Accountant", "senior"),
    ("Sr. Nurse", "senior"),
    ("Desarrollador Semi Senior", "mid"),
    ("Analista SSR", "mid"),
    ("Junior Electrician", "junior"),
    ("Pasante de Marketing", "intern"),
    ("Team Lead - Customer Support", "lead"),
    ("Head of Sales", "lead"),
    ("Jefa de Enfermería", "lead"),
    # Palabras que son parte del ROL, no del nivel: no deben inferir seniority.
    ("Account Manager", "unknown"),
    ("Community Manager", "unknown"),
    ("Staff Nurse", "unknown"),
    ("Lead Generation Specialist", "unknown"),
    ("Mid-Market Account Executive", "unknown"),
    ("Profesor de Matemática", "unknown"),
])
def test_detect_seniority_from_title(title, expected):
    assert normalize.detect_seniority(title) == expected


def test_seniority_description_only_counts_explicit_level():
    assert normalize.detect_seniority("Contador", "Nivel: Semi Senior. Trabajarás con seniors.") == "mid"
    assert normalize.detect_seniority("Contador", "Trabajarás junto a contadores senior.") == "unknown"


@pytest.mark.parametrize("kwargs,expected", [
    ({"remote": True}, "remote"),
    ({"location": "Remote - LATAM"}, "remote"),
    ({"title": "Enfermero (híbrido)"}, "hybrid"),
    ({"location": "Buenos Aires", "description": "Modalidad presencial en nuestra sede."}, "onsite"),
    ({"location": "Madrid", "description": "Trabajo remoto 100% remoto"}, "remote"),
    # "remote" suelto en beneficios no alcanza para decir que el puesto es remoto.
    ({"location": "Lima", "description": "Beneficios: un día remote al mes"}, "unknown"),
    ({"remote": True, "location": "Hybrid - Berlin"}, "hybrid"),
])
def test_detect_modality(kwargs, expected):
    assert normalize.detect_modality(make_job(**kwargs)) == expected


def test_enrich_sets_all_fields():
    job = normalize.enrich(make_job(title="Senior Contador", description="Buscamos una persona con experiencia para la empresa y el equipo de trabajo", remote=True))
    assert (job.language, job.seniority, job.modality) == ("es", "senior", "remote")


def test_dedupe_same_company_similar_title_keeps_longer_description():
    a = make_job(title="Enfermero/a (m/w/d)", company="Clínica Ficticia S.A.", description="corta", jid="a")
    b = make_job(title="Enfermero/a", company="Clinica Ficticia", description="descripción mucho más larga", jid="b")
    c = make_job(title="Enfermero/a", company="Otra Clínica", description="x", jid="c")
    result = normalize.dedupe([a, b, c])
    assert [j.id for j in result] == ["b", "c"]


def test_dedupe_keeps_different_titles_same_company():
    a = make_job(title="Contador Senior", company="ACME", jid="a")
    b = make_job(title="Asistente Administrativo", company="ACME", jid="b")
    assert len(normalize.dedupe([a, b])) == 2
