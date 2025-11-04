"""
TenderIQ Repository Layer

Encapsulates all data access logic for TenderIQ features.
Abstracts away the scraper database schema and provides TenderIQ-specific queries.

This separation ensures TenderIQ module doesn't directly depend on ScraperRepository,
making the modules properly decoupled and independently testable.
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload

from app.modules.scraper.db.schema import (
    ScrapeRun,
    ScrapedTender,
    ScrapedTenderQuery,
)


class TenderIQRepository:
    """Repository for TenderIQ-specific data access operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_available_scrape_runs(self) -> list[ScrapeRun]:
        """
        Get all distinct scrape runs ordered by most recent first.
        Eagerly loads all relationships for efficient access.

        Used by frontend to populate date selector dropdown.

        Ordered by tender_release_date (when tenders were released),
        not run_at (when we scraped them).

        Returns:
            List of ScrapeRun objects with all relationships loaded
        """
        return (
            self.db.query(ScrapeRun)
            .order_by(ScrapeRun.tender_release_date.desc())
            .options(
                joinedload(ScrapeRun.queries).joinedload(ScrapedTenderQuery.tenders)
            )
            .all()
        )

    def get_scrape_runs_by_date_range(
        self, days: Optional[int] = None
    ) -> list[ScrapeRun]:
        """
        Get scrape runs from a specific date range based on tender_release_date.

        Uses tender_release_date (when tenders were released from website header),
        not run_at (when we scraped them), for consistent grouping.

        Args:
            days: Number of days to look back. None means all historical data.

        Returns:
            List of ScrapeRun objects ordered by tender_release_date DESC (newest first)

        Example:
            get_scrape_runs_by_date_range(5)  # Last 5 days of releases
            get_scrape_runs_by_date_range()   # All historical data
        """
        query = self.db.query(ScrapeRun)

        if days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            # Filter by tender_release_date, not run_at
            query = query.filter(ScrapeRun.tender_release_date >= cutoff_date.date())

        return query.order_by(ScrapeRun.tender_release_date.desc()).all()

    def get_tenders_by_scrape_run(
        self,
        scrape_run_id,
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> list[ScrapedTender]:
        """
        Get all tenders from a specific scrape run with optional filters.

        Args:
            scrape_run_id: UUID of the ScrapeRun
            category: Filter by query_name (e.g., "Civil", "Electrical")
            location: Filter by city
            min_value: Filter by minimum tender value (in crore)
            max_value: Filter by maximum tender value (in crore)

        Returns:
            List of ScrapedTender objects matching filters

        Example:
            get_tenders_by_scrape_run(run_id, category="Civil", location="Mumbai")
        """
        query = (
            self.db.query(ScrapedTender)
            .join(ScrapedTenderQuery)
            .filter(ScrapedTenderQuery.scrape_run_id == scrape_run_id)
            .options(joinedload(ScrapedTender.files))
        )

        if category:
            query = query.filter(ScrapedTenderQuery.query_name == category)

        if location:
            query = query.filter(ScrapedTender.city == location)

        # Note: min_value and max_value are stored as strings in DB
        # Would need parsing for true numeric comparison
        # For now, leaving as extension point

        return query.all()

    def get_tenders_by_specific_date(
        self,
        date: str,  # Format: "YYYY-MM-DD"
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> list[ScrapedTender]:
        """
        Get all tenders released on a specific date (tender_release_date).

        Uses tender_release_date (when tenders were released from website header),
        not run_at (when we scraped them).

        Args:
            date: Date string in format "YYYY-MM-DD"
            category: Filter by query_name
            location: Filter by city
            min_value: Filter by minimum tender value
            max_value: Filter by maximum tender value

        Returns:
            List of ScrapedTender objects from that date

        Raises:
            ValueError: If date format is invalid

        Example:
            get_tenders_by_specific_date("2024-11-03", category="Civil")
        """
        try:
            from datetime import datetime as dt, date as date_type

            # Parse the date string to date object (not datetime)
            target_date = dt.strptime(date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Invalid date format. Expected YYYY-MM-DD, got '{date}'"
            ) from e

        # Query for tenders released on this specific date using tender_release_date
        query = (
            self.db.query(ScrapedTender)
            .join(ScrapedTenderQuery)
            .join(ScrapeRun)
            .filter(ScrapeRun.tender_release_date == target_date)
            .options(joinedload(ScrapedTender.files))
        )

        if category:
            query = query.filter(ScrapedTenderQuery.query_name == category)

        if location:
            query = query.filter(ScrapedTender.city == location)

        return query.all()

    def get_all_tenders_with_filters(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> list[ScrapedTender]:
        """
        Get all tenders in the system with optional filters.

        Args:
            category: Filter by query_name
            location: Filter by city
            min_value: Filter by minimum tender value
            max_value: Filter by maximum tender value

        Returns:
            List of all ScrapedTender objects matching filters
        """
        query = self.db.query(ScrapedTender).options(joinedload(ScrapedTender.files))

        if category:
            query = query.join(ScrapedTenderQuery).filter(
                ScrapedTenderQuery.query_name == category
            )

        if location:
            query = query.filter(ScrapedTender.city == location)

        return query.all()
