import time
from email_fetcher import process_email_fetch_jobs
from process_email_regex import main
from config import CRON_INTERVAL

def run_scheduler():
    """Run the email fetch job processing in a loop with the specified interval."""
    while True:
        print("Checking for pending email regex jobs...")
        main()
        # Wait for the specified interval before checking again
        time.sleep(CRON_INTERVAL)

if __name__ == "__main__":
    run_scheduler()
