import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from premailer import transform
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime

import requests
import re
import json
import os

# Local modules
from app.db.database import SessionLocal
from app.modules.scraper.db.repository import ScraperRepository
from .detail_page_scrape import scrape_tender
# from .drive import authenticate_google_drive, download_folders, get_shareable_link, upload_folder_to_drive
from .email_sender import listen_and_get_link, listen_and_get_unprocessed_emails, send_html_email
from .home_page_scrape import scrape_page
from .services.dms_integration_service import process_tenders_for_dms
from .templater import generate_email, reformat_page
from .progress_tracker import ProgressTracker, ScrapeSection, logger

load_dotenv()

GOOGLE_DRIVE_PARENT_FOLDER = os.getenv("GOOGLE_DRIVE_PARENT_FOLDER")
base_url = "https://www.tenderdetail.com"
tdr_xpath = "/html/body/div/div[1]/section[2]/div[1]/div/div/table[1]/tbody/tr[2]/td[2]"

def clean_project():
    # First lets clear the tenders/ directory
    os.system("rm -rf tenders/")
    # Create the tenders/ directory
    os.mkdir("tenders/")

def insert_drive_links(soup: BeautifulSoup):
    soup2 = BeautifulSoup(open("./final.html"), 'html.parser')
    soup1_tenders_links = soup.find_all('a', attrs={'class': 'tender_table_view_tender_link'})
    soup2_tenders_links = soup2.find_all('p', attrs={'class': 'm-td-brief-link'})

    # Replace the links in soup1 with the google drive links in soup2
    # Iterate through both lists at the same time
    for tender1, tender2 in zip(soup1_tenders_links, soup2_tenders_links):
        tender1['href'] = tender2.find_all('a')[0]['href']

def scrape_link(link: str, source_priority: str = "normal", skip_dedup_check: bool = False):
    """
    Main scraping function with comprehensive progress tracking and logging.
    Supports both manual link pasting and email-based scraping with unified deduplication.

    Flow:
    1. Check for duplicates (with priority-based conflict resolution)
    2. Scrape home page
    3. Scrape detail pages for each tender
    4. DMS integration
    5. Save to database
    6. Log processing and generate/send email

    Args:
        link: The tender URL to scrape
        source_priority: "low", "normal", or "high" - used for conflict resolution when same tender from multiple sources
        skip_dedup_check: If True, skip deduplication check (use with caution, mainly for testing)
    """
    tracker = ProgressTracker(verbose=True)
    start_time = datetime.now()

    try:
        # Initialize database connection for deduplication check
        db = SessionLocal()
        scraper_repo = ScraperRepository(db)

        # Step 0: Deduplication Check (before any scraping)
        if not skip_dedup_check:
            with ScrapeSection(tracker, "Deduplication Check"):
                is_duplicate, existing_log = scraper_repo.check_tender_duplicate_with_priority(link, source_priority)

                if is_duplicate:
                    logger.info(f"⏭️  DUPLICATE TENDER DETECTED: {link}")
                    logger.info(f"   Previously processed by: {existing_log.email_sender} on {existing_log.processed_at}")

                    priority_order = {"low": 0, "normal": 1, "high": 2}
                    source_level = priority_order.get(source_priority, 1)
                    existing_level = priority_order.get(existing_log.priority, 1)

                    if source_level > existing_level:
                        logger.info(f"   ✅ Higher priority detected! Re-processing tender...")
                        # Mark old one as superseded
                        scraper_repo.mark_superseded(
                            str(existing_log.id),
                            f"Reprocessed with higher priority ({source_priority})"
                        )
                        logger.info(f"   Marked previous entry as superseded")
                    else:
                        logger.warning(f"   ⚠️  Same or lower priority. Skipping scrape.")
                        logger.info(f"   To re-scrape, use source_priority='high'")

                        # Log this as skipped
                        scraper_repo.log_email_processing(
                            email_uid="manual" if source_priority != "normal" else "duplicate_check",
                            email_sender="manual_override" if source_priority != "normal" else "automatic",
                            email_received_at=datetime.utcnow(),
                            tender_url=link,
                            processing_status="skipped",
                            error_message=f"Duplicate tender (existing: {existing_log.priority}, new: {source_priority})",
                            priority=source_priority
                        )
                        db.close()
                        tracker.close_all_progress_bars()
                        return
                else:
                    logger.info(f"✅ No duplicates found. Proceeding with scrape...")
        db.close()

        with ScrapeSection(tracker, "Homepage Scraping"):
            logger.info(f"📍 Starting scrape of: {link}")
            homepage = scrape_page(link)
            total_tenders = sum(len(q.tenders) for q in homepage.query_table)
            logger.info(f"📊 Found {total_tenders} tenders across {len(homepage.query_table)} categories")

            for query in homepage.query_table:
                logger.info(f"   📋 {query.query_name}: {len(query.tenders)} tenders")

        removed_tenders = {}

        # Create progress bar for detail page scraping
        total_tenders = sum(len(q.tenders) for q in homepage.query_table)
        detail_progress = tracker.create_detail_scrape_progress_bar(total_tenders)

        with ScrapeSection(tracker, "Detail Page Scraping"):
            for query_table in homepage.query_table:
                query_progress = tracker.create_query_progress_bar(
                    query_table.query_name,
                    len(query_table.tenders)
                )

                tenders_to_remove = []
                for tender in query_table.tenders:
                    try:
                        logger.debug(f"🎯 Scraping detail page for: {tender.tender_name}")
                        tender.details = scrape_tender(tender.tender_url)
                        logger.debug(f"✅ Detail page scraped: {tender.tender_name}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to scrape details for {tender.tender_name}: {str(e)}")
                        tenders_to_remove.append(tender)
                        removed_tenders[tender.tender_id] = json.loads(
                            tender.model_dump_json(indent=2)
                        )

                    if query_progress:
                        query_progress.update(1)
                    if detail_progress:
                        detail_progress.update(1)

                # Remove tenders after iteration to avoid list modification during iteration
                for tender in tenders_to_remove:
                    query_table.tenders.remove(tender)

                if query_progress:
                    query_progress.close()

            if detail_progress:
                detail_progress.close()

            if removed_tenders:
                logger.warning(f"⚠️  Removed {len(removed_tenders)} tenders due to scraping errors")
            logger.info(f"✅ Detail page scraping completed for {total_tenders - len(removed_tenders)} tenders")

        # Database operations
        db_save_progress = tracker.create_database_save_progress_bar(1)

        db = SessionLocal()
        try:
            with ScrapeSection(tracker, "DMS Integration & Database Save"):
                logger.info("🔄 Processing tenders for DMS integration...")
                homepage, tender_release_date = process_tenders_for_dms(db, homepage)
                tracker.update_progress("database", 1, "DMS integration completed")

                logger.info("💾 Saving scraped data to database...")
                scraper_repo = ScraperRepository(db)
                scraper_repo.create_scrape_run(homepage, tender_release_date)
                tracker.update_progress("database", 1, "Database save completed")

                num_tenders = sum(len(q.tenders) for q in homepage.query_table)
                logger.info(f"✅ Successfully saved {num_tenders} tenders to database")

        except Exception as e:
            logger.error(f"❌ Critical error during DMS integration or database save", e)
            db.rollback()
            tracker.log_error("Database operation failed", e)
            raise
        finally:
            db.close()
            if db_save_progress:
                db_save_progress.close()
            logger.info("🔒 Database session closed")

        # Email generation and sending
        with ScrapeSection(tracker, "Email Generation & Sending"):
            logger.info("📧 Generating email template...")
            generated_template = generate_email(homepage)

            logger.info("💾 Writing HTML files...")
            with open("email.html", "w") as f:
                f.write(generated_template.prettify())

            if removed_tenders:
                with open("removed_tenders.json", "w") as f:
                    f.write(json.dumps(removed_tenders))
                logger.info(f"📝 Wrote removed_tenders.json with {len(removed_tenders)} entries")

            logger.info("📤 Sending email...")
            send_html_email(generated_template)
            logger.info("✅ Email sent successfully")

        # Log final statistics
        duration = (datetime.now() - start_time).total_seconds()
        final_tender_count = sum(len(q.tenders) for q in homepage.query_table)

        tracker.log_summary({
            "Total Tenders Processed": final_tender_count,
            "Tenders Removed (Errors)": len(removed_tenders),
            "Duration": f"{duration:.2f}s",
            "Status": "✅ SUCCESS"
        })

    except Exception as e:
        tracker.log_error("❌ Fatal error in scrape_link", e)
        raise
    finally:
        tracker.close_all_progress_bars()

def listen_email():
    """
    Email listening loop with progress tracking and comprehensive logging.

    Flow:
    1. Fetch ALL emails from tenders@tenderdetail.com (read or unread)
    2. For each email, extract the tender URL
    3. Check if email+tender has been processed before (deduplication)
    4. Check if tender URL has been processed from ANY email
    5. If not processed, scrape it and log in database
    6. Wait 5 minutes and repeat

    This avoids the "user reads email → listener can't find it" bug.
    """
    tracker = ProgressTracker(verbose=True)
    cycle_number = 0

    while True:
        cycle_number += 1
        cycle_start = datetime.now()

        with ScrapeSection(tracker, f"Email Polling Cycle #{cycle_number}"):
            db = SessionLocal()
            try:
                scraper_repo = ScraperRepository(db)

                # 1. Get all emails from last 24 hours
                logger.info("📧 Fetching unprocessed emails...")
                emails_data = listen_and_get_unprocessed_emails()

                if not emails_data:
                    logger.info("ℹ️  No emails from target senders found.")
                    db.close()
                    continue  # Skip to sleep and retry in next cycle

                logger.info(f"📊 Found {len(emails_data)} emails with tender URLs")

                # Create progress bar for email processing
                email_progress = tracker.create_email_progress_bar(len(emails_data))

                # 2. Process each email
                processed_count = 0
                skipped_count = 0
                failed_count = 0

                # Create deduplication progress bar
                dedup_progress = tracker.create_deduplication_progress_bar(len(emails_data))

                for email_info in emails_data:
                    email_uid = email_info['email_uid']
                    email_sender = email_info['email_sender']
                    email_date = email_info['email_date']
                    tender_url = email_info['tender_url']

                    logger.debug(f"📋 Checking email {email_uid} from {email_sender}")

                    # 3. Check if this email+tender combination has been processed
                    if scraper_repo.has_email_been_processed(email_uid, tender_url):
                        logger.info(f"⏭️  Skipping (duplicate email+tender): {tender_url}")
                        scraper_repo.log_email_processing(
                            email_uid=email_uid,
                            email_sender=email_sender,
                            email_received_at=email_date,
                            tender_url=tender_url,
                            processing_status="skipped",
                            error_message="Email+tender combination already processed"
                        )
                        skipped_count += 1
                        if dedup_progress:
                            dedup_progress.update(1)
                        if email_progress:
                            email_progress.update(1)
                        continue

                    # 4. Check if this tender URL has been processed from ANY email
                    if scraper_repo.has_tender_url_been_processed(tender_url):
                        logger.info(f"⏭️  Skipping (duplicate URL): {tender_url}")
                        scraper_repo.log_email_processing(
                            email_uid=email_uid,
                            email_sender=email_sender,
                            email_received_at=email_date,
                            tender_url=tender_url,
                            processing_status="skipped",
                            error_message="Tender URL already processed"
                        )
                        skipped_count += 1
                        if dedup_progress:
                            dedup_progress.update(1)
                        if email_progress:
                            email_progress.update(1)
                        continue

                    # 5. This is a new email → Scrape it!
                    logger.info(f"🚀 NEW email detected! Processing tender: {tender_url}")
                    try:
                        # Close the current session for the scrape
                        db.close()

                        # Call the scraping function with progress tracking
                        scrape_link(tender_url)

                        # Re-open session for logging
                        db = SessionLocal()
                        scraper_repo = ScraperRepository(db)

                        # Log successful processing
                        scraper_repo.log_email_processing(
                            email_uid=email_uid,
                            email_sender=email_sender,
                            email_received_at=email_date,
                            tender_url=tender_url,
                            processing_status="success"
                        )

                        logger.info(f"✅ Successfully processed new tender from email")
                        processed_count += 1

                    except Exception as e:
                        logger.error(f"❌ Error during scrape of {tender_url}", e)
                        # Log the failure
                        scraper_repo.log_email_processing(
                            email_uid=email_uid,
                            email_sender=email_sender,
                            email_received_at=email_date,
                            tender_url=tender_url,
                            processing_status="failed",
                            error_message=str(e)
                        )
                        failed_count += 1

                    if dedup_progress:
                        dedup_progress.update(1)
                    if email_progress:
                        email_progress.update(1)

                # Close progress bars
                if dedup_progress:
                    dedup_progress.close()
                if email_progress:
                    email_progress.close()

                # Log cycle summary
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                tracker.log_stats({
                    "Total Emails": len(emails_data),
                    "Processed (New)": processed_count,
                    "Skipped (Duplicates)": skipped_count,
                    "Failed": failed_count,
                    "Cycle Duration": f"{cycle_duration:.2f}s"
                })

            except Exception as e:
                logger.error(f"❌ Critical error in listen_email cycle", e)
                db.rollback()
            finally:
                db.close()

        # 7. Wait for 5 minutes before checking again
        sleep_duration_seconds = 300
        logger.info(f"\n{'='*60}")
        logger.info(f"⏳ Next check in {sleep_duration_seconds / 60} minutes...")
        logger.info(f"{'='*60}\n")
        time.sleep(sleep_duration_seconds)


def listen_email_old():
    """
    DEPRECATED: Old implementation using UNSEEN flag.
    Kept for reference but use listen_email() instead.
    """
    while True:
        print("\n--- Starting new cycle: Listening for trigger email ---")

        # 1. Call the listener to get a link
        link_to_scrape = listen_and_get_link()

        # 2. If a link is found, run the scraper
        if link_to_scrape:
            print(f"🚀 Link found! Starting scrape for: {link_to_scrape}")
            try:
                scrape_link(link_to_scrape) # Your existing scraping function
                print("✅ Scraping and email sending process completed successfully.")
            except Exception as e:
                print(f"❌ An error occurred during the scrape/send process: {e}")
        else:
            print("No new trigger email found.")

        # 3. Wait for 5 minutes before checking again
        sleep_duration_seconds = 300
        print(f"--- Cycle complete. Waiting for {sleep_duration_seconds / 60} minutes... ---")
        time.sleep(sleep_duration_seconds)
    
if __name__ == "__main__":
    """
    Main workflow: Continuously listens for emails, and when a valid link is
    found, triggers the scraping and sending process.
    """
    print("Select a start mode: ")
    print("1. Paste a link")
    print("2. Listen for emails")

    choice = input("Enter your choice (1/2): ")

    if choice == '1':
        link_to_scrape = input("Enter the link to scrape: ")
        if link_to_scrape == "":
            link_to_scrape = "https://www.tenderdetail.com/dailytenders/47136136/7c7651b5-98f3-4956-9404-913de95abb79"
        scrape_link(link_to_scrape)
        print("✅ Scraping and email sending process completed successfully.")

    elif choice == '2':
        listen_email()

    else:
        print("Invalid choice. Please select 1 or 2.")
