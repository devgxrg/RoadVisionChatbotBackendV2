from typing import List
from sqlalchemy.orm import Session

from app.modules.scraper.db.schema import ScrapeRun, ScrapedTenderQuery


def get_all_categories(db: Session, scrape_run: ScrapeRun) -> List[ScrapedTenderQuery]:
    scrape_run_id = ScrapeRun.id
    return db.query(ScrapedTenderQuery).filter_by(scrape_run_id=scrape_run_id).filter(ScrapedTenderQuery.query_name.like("%Civil%")).all()

def get_scrape_runs(db: Session) -> List[ScrapeRun]:
    scrape_runs = db.query(ScrapeRun).all()
    return scrape_runs
