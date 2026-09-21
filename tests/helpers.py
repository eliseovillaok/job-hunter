from scrapers import JobPosting


def make_job(title="Analista contable", company="Empresa Ficticia SA", description="", location="",
             remote=False, jid=None, **kw) -> JobPosting:
    return JobPosting(
        id=jid or f"t-{abs(hash((title, company, description))) % 10**8}",
        title=title, company=company, description=description, location=location,
        remote=remote, url="https://example.com/job", source="Test", **kw,
    )
