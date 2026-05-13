"""
main.py — Orquestador principal del Job Hunter
Uso: python main.py [--dry-run] [--no-email]
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from scrapers import get_all_jobs
from ai_engine import process_jobs
from notifier import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("job_hunter.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


def save_results(scored_jobs, output_dir: Path):
    """Guarda resultados en JSON para historial."""
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = output_dir / f"results_{timestamp}.json"

    data = []
    for sj in scored_jobs:
        data.append({
            "score": sj.score,
            "title": sj.job.title,
            "company": sj.job.company,
            "source": sj.job.source,
            "url": sj.job.url,
            "remote": sj.job.remote,
            "match_reasons": sj.match_reasons,
            "missing_skills": sj.missing_skills,
            "summary": sj.summary,
            "has_cover_letter": sj.cover_letter is not None,
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log.info(f"Resultados guardados en {output_file}")
    return output_file


def print_summary(scored_jobs):
    """Imprime resumen en consola."""
    top = [j for j in scored_jobs if j.cover_letter]

    print("\n" + "="*60)
    print("📊 RESUMEN DEL RUN")
    print("="*60)
    print(f"Total ofertas analizadas : {len(scored_jobs)}")
    print(f"Matches sobre umbral      : {len(top)}")
    print()

    if top:
        print("🎯 TOP MATCHES:")
        for sj in top:
            bar = "█" * (sj.score // 10) + "░" * (10 - sj.score // 10)
            print(f"  {sj.score:3d}/100 [{bar}] {sj.job.title[:40]:<40} @ {sj.job.company[:25]:<25} [{sj.job.source}]")
            print(f"           {sj.job.url}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Job Hunter — Automatización de búsqueda laboral")
    parser.add_argument("--dry-run",  action="store_true", help="No enviar email, solo mostrar resultados")
    parser.add_argument("--no-email", action="store_true", help="Saltar envío de email")
    parser.add_argument("--output",   default="results",   help="Directorio de output (default: ./results)")
    args = parser.parse_args()

    log.info("🚀 Iniciando Job Hunter")
    log.info(f"Modo: {'DRY RUN' if args.dry_run else 'PRODUCCIÓN'}")
    start = datetime.now()

    # STEP 1: Scraping
    log.info("STEP 1/3 — Scraping de plataformas")
    jobs = get_all_jobs()

    if not jobs:
        log.warning("No se encontraron ofertas. Verificá conexión o palabras clave.")
        sys.exit(0)

    # STEP 2: AI Processing
    log.info("STEP 2/3 — Evaluación con IA y generación de cover letters")
    scored_jobs = process_jobs(jobs)

    # STEP 3: Output
    log.info("STEP 3/3 — Enviando resultados")
    print_summary(scored_jobs)
    save_results(scored_jobs, Path(args.output))

    if not args.dry_run and not args.no_email:
        send_digest(scored_jobs)
    else:
        log.info("Email omitido (--dry-run o --no-email activo)")

    elapsed = (datetime.now() - start).seconds
    log.info(f"✅ Finalizado en {elapsed}s")


if __name__ == "__main__":
    main()
