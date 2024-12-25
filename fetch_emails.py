import time
from email_fetcher import process_email_fetch_jobs
from process_email_regex import main
from config import CRON_INTERVAL_IN_SECONDS_SCHEDULER1, CRON_DURATION_IN_MINUTES_SCHEDULER1

def run_scheduler():
    """Run the email fetch job processing for a limited duration."""
    start_time = time.time() 
    end_time = start_time + CRON_DURATION_IN_MINUTES_SCHEDULER1 * 60 

    while time.time() < end_time:
        print("Checking for pending email fetch jobs...")
        process_email_fetch_jobs()
        time.sleep(CRON_INTERVAL_IN_SECONDS_SCHEDULER1)

    print("Scheduler run completed. Exiting.")

if __name__ == "__main__":
    run_scheduler()