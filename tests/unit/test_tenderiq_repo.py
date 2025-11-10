
from app.db.database import SessionLocal
from app.modules.tenderiq.repositories import repository as repo

from app.modules.tenderiq.services import tender_service_sse as service
import json

db = SessionLocal()

scrape_runs = repo.get_scrape_runs(db)
latest_scrape_run = scrape_runs[0]
categories_of_current_day = repo.get_all_categories(db, latest_scrape_run)

daily_tenders = service.get_daily_tenders_sse(db)
print(daily_tenders)
