from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from app.modules.tenderiq.models.pydantic_models import DailyTendersResponse
from app.modules.tenderiq.repositories import repository as tenderiq_repo

def get_daily_tenders_sse(db: Session):

    scrape_runs = tenderiq_repo.get_scrape_runs(db)
    latest_scrape_run = scrape_runs[-1]
    categories_of_current_day = tenderiq_repo.get_all_categories(db, latest_scrape_run)
    print(latest_scrape_run.no_of_new_tenders)

    to_return = DailyTendersResponse(
        id = latest_scrape_run.id,
        run_at = latest_scrape_run.run_at,
        date_str = latest_scrape_run.date_str,
        name = latest_scrape_run.name,
        contact = latest_scrape_run.contact,
        no_of_new_tenders = latest_scrape_run.no_of_new_tenders,
        company = latest_scrape_run.company,
        queries = categories_of_current_day
    )

    return to_return
