import threading
import time
import asyncio
import logging
from django.utils import timezone
from .tasks import fast_ingest_and_save, background_scrape_all_pending

logger = logging.getLogger(__name__)

def run_scheduler_loop():
    print("SignalReport: Starting background periodic ingestion loop...", flush=True)
    logger.info("SignalReport: Starting background periodic ingestion loop...")
    # Add a short delay on startup to allow the server to fully initialize
    time.sleep(5)
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("SignalReport Scheduler: Triggering news ingestion...", flush=True)
            logger.info("SignalReport Scheduler: Triggering news ingestion...")
            loop.run_until_complete(fast_ingest_and_save(is_historical=False))
            print("SignalReport Scheduler: Triggering background scraping...", flush=True)
            logger.info("SignalReport Scheduler: Triggering background scraping...")
            loop.run_until_complete(background_scrape_all_pending())
            loop.close()
        except Exception as e:
            print(f"SignalReport Scheduler loop error: {str(e)}", flush=True)
            logger.error(f"SignalReport Scheduler loop encountered error: {str(e)}")
        
        # Sleep for 10 minutes (600 seconds)
        time.sleep(600)

def start_scheduler():
    import os
    import sys
    
    # Standard check to prevent double execution in Django's auto-reloader
    is_runserver = 'runserver' in sys.argv
    if not is_runserver or '--noreload' in sys.argv or os.environ.get('RUN_MAIN') == 'true':
        thread = threading.Thread(target=run_scheduler_loop, name="SignalReportScheduler")
        thread.daemon = True
        thread.start()
        print("SignalReport: Background periodic ingestion scheduler thread started.", flush=True)
        logger.info("SignalReport: Background periodic ingestion scheduler thread started.")
