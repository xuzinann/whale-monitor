#!/usr/bin/env python3
"""
Whale Monitor - Main Application
Monitors whale wallet transactions and sends daily Discord digests.
"""
import sys
import time
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add src to path
sys.path.insert(0, 'src')

from config import Config
from monitor import WhaleMonitor
from database import WhaleDatabase
from analyzer import SignificanceAnalyzer
from notifier import DiscordNotifier


class WhaleMonitorApp:
    """Main application coordinating all components."""

    def __init__(self, config: Config):
        self.config = config
        print("\n" + "=" * 60)
        print("         WHALE MONITOR APPLICATION")
        print("=" * 60 + "\n")

        # Validate configuration
        if not config.validate():
            print("[ERROR] Configuration validation failed. Exiting.")
            sys.exit(1)

        config.print_config()

        # Initialize components
        print("Initializing components...\n")

        self.monitor = WhaleMonitor(api_key=config.BLOCKCYPHER_API_KEY)
        self.database = WhaleDatabase(db_path=config.DATABASE_PATH)
        self.analyzer = SignificanceAnalyzer(self.database, thresholds=config.get_thresholds())
        self.notifier = DiscordNotifier(webhook_url=config.DISCORD_WEBHOOK_URL)

        # Send test message
        print("Sending test message to Discord...")
        if self.notifier.send_test_message():
            print("[OK] Discord connection verified\n")
        else:
            print("[WARNING] Failed to send test message. Check webhook URL.\n")

        self.scheduler = None
        self.last_digest_date = None

    def check_wallets_job(self):
        """Periodic job to check all wallets for new transactions."""
        print(f"\n{'='*60}")
        print(f"Running wallet check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        try:
            new_txs = self.monitor.check_all_wallets()

            if new_txs > 0:
                print(f"\n[OK] Found {new_txs} new transactions")

                # Optionally send alerts for highly significant transactions (score >= 8)
                # Uncomment below to enable immediate alerts
                # self._send_immediate_alerts()

        except Exception as e:
            print(f"[ERROR] Wallet check failed: {e}")

    def _send_immediate_alerts(self):
        """Send immediate alerts for highly significant transactions."""
        significant_txs = self.analyzer.get_significant_transactions(
            coin_type=None,
            hours=1,  # Last hour
            min_score=8  # Very high significance
        )

        for tx in significant_txs:
            self.notifier.send_significant_transaction_alert(tx, tx['analysis'])
            time.sleep(1)  # Rate limit

    def send_daily_digest_job(self):
        """Job to send daily digest."""
        today = datetime.now().strftime('%Y-%m-%d')

        # Prevent duplicate digests
        if self.last_digest_date == today:
            print(f"[INFO] Digest already sent for {today}, skipping")
            return

        print(f"\n{'='*60}")
        print(f"Generating daily digest for {today}")
        print(f"{'='*60}\n")

        try:
            # Generate summaries for each coin
            summaries = {}

            for coin_type in ['BTC', 'DOGE', 'LTC']:
                print(f"Analyzing {coin_type} activity...")
                summaries[coin_type] = self.analyzer.generate_summary_stats(coin_type, hours=24)

            # Send digest
            if self.notifier.send_daily_digest(today, summaries):
                self.last_digest_date = today
                print(f"\n[OK] Daily digest sent successfully")
            else:
                print(f"\n[ERROR] Failed to send daily digest")

            # Cleanup old transactions (keep last 30 days)
            self.database.cleanup_old_transactions(days=30)

        except Exception as e:
            print(f"[ERROR] Failed to generate/send digest: {e}")

    def run_continuous(self):
        """Run continuous monitoring with scheduling."""
        print("\n" + "=" * 60)
        print("Starting continuous monitoring...")
        print("=" * 60 + "\n")

        # Create scheduler
        timezone = pytz.timezone(self.config.NOTIFICATION_TIMEZONE)
        self.scheduler = BlockingScheduler(timezone=timezone)

        # Schedule periodic wallet checks
        check_interval = self.config.POLL_INTERVAL_MINUTES
        self.scheduler.add_job(
            self.check_wallets_job,
            'interval',
            minutes=check_interval,
            id='wallet_check',
            next_run_time=datetime.now()  # Run immediately
        )

        print(f"[OK] Scheduled wallet checks every {check_interval} minutes")

        # Schedule daily digest
        digest_time = self.config.NOTIFICATION_TIME
        hour, minute = map(int, digest_time.split(':'))

        digest_trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=timezone
        )

        self.scheduler.add_job(
            self.send_daily_digest_job,
            trigger=digest_trigger,
            id='daily_digest'
        )

        print(f"[OK] Scheduled daily digest at {digest_time} {self.config.NOTIFICATION_TIMEZONE}")

        print("\n" + "=" * 60)
        print("Whale Monitor is now running!")
        print("Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n\n[OK] Shutting down gracefully...")
            self.cleanup()

    def run_once(self):
        """Run a single check and exit (for testing)."""
        print("[INFO] Running single check mode\n")
        self.check_wallets_job()
        self.cleanup()

    def send_digest_now(self):
        """Send digest immediately (for testing)."""
        print("[INFO] Sending digest now\n")
        self.send_daily_digest_job()
        self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        print("\n=== Cleaning up ===")
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.database.close()
        print("[OK] Cleanup complete")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Whale Monitor - Track cryptocurrency whale transactions')

    parser.add_argument(
        '--mode',
        choices=['continuous', 'once', 'digest'],
        default='continuous',
        help='Run mode: continuous monitoring, single check, or send digest now'
    )

    parser.add_argument(
        '--config',
        help='Path to .env config file'
    )

    args = parser.parse_args()

    # Load configuration
    config = Config(env_file=args.config)

    # Create app
    app = WhaleMonitorApp(config)

    # Run based on mode
    if args.mode == 'continuous':
        app.run_continuous()
    elif args.mode == 'once':
        app.run_once()
    elif args.mode == 'digest':
        app.send_digest_now()


if __name__ == "__main__":
    main()
