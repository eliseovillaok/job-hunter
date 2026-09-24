from scrapers import JobPosting

PASSWORD = "clave-ficticia-1"


def make_job(title="Analista contable", company="Empresa Ficticia SA", description="", location="",
             remote=False, jid=None, **kw) -> JobPosting:
    return JobPosting(
        id=jid or f"t-{abs(hash((title, company, description))) % 10**8}",
        title=title, company=company, description=description, location=location,
        remote=remote, url="https://example.com/job", source="Test", **kw,
    )


def with_csrf(client):
    """Toma el token CSRF de la cookie y lo manda en cada pedido, como hace app.js."""
    if not client.cookies.get("jh_csrf"):
        client.get("/ingresar")
    client.headers["X-CSRF-Token"] = client.cookies.get("jh_csrf")
    return client


def sign_up(client, email="persona@example.com", password=PASSWORD):
    """Crea la cuenta por la pantalla real y deja al cliente adentro."""
    with_csrf(client)
    r = client.post("/crear-cuenta", data={"email": email, "password": password}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return client
