"""
Configuration management for whale monitor.
Loads settings from .env file with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Application configuration."""

    def __init__(self, env_file: str = None):
        # Try to load .env file
        if env_file:
            load_dotenv(env_file)
        else:
            # Try common locations
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                print(f"[OK] Loaded configuration from {env_path}")
            else:
                print(f"[WARNING] No .env file found. Using defaults.")

        # Discord Configuration
        self.DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

        if not self.DISCORD_WEBHOOK_URL:
            print("[WARNING] DISCORD_WEBHOOK_URL not set!")

        # Notification Schedule
        self.NOTIFICATION_TIME = os.getenv('NOTIFICATION_TIME', '20:00')
        self.NOTIFICATION_TIMEZONE = os.getenv('NOTIFICATION_TIMEZONE', 'America/New_York')

        # API Keys
        self.BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY', '')

        # Transaction Thresholds
        self.BTC_LARGE_TX_THRESHOLD = float(os.getenv('BTC_LARGE_TX_THRESHOLD', '50'))
        self.DOGE_LARGE_TX_THRESHOLD = float(os.getenv('DOGE_LARGE_TX_THRESHOLD', '10000000'))
        self.LTC_LARGE_TX_THRESHOLD = float(os.getenv('LTC_LARGE_TX_THRESHOLD', '5000'))

        # Monitoring Settings
        self.POLL_INTERVAL_MINUTES = int(os.getenv('POLL_INTERVAL_MINUTES', '10'))

        # Database path
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/whale_monitor.db')

        # Data directory
        self.DATA_DIR = os.getenv('DATA_DIR', 'data')

    def get_thresholds(self):
        """Get transaction thresholds as dict."""
        return {
            'BTC': {
                'large_tx': self.BTC_LARGE_TX_THRESHOLD,
                'usd': 1000000  # $1M
            },
            'DOGE': {
                'large_tx': self.DOGE_LARGE_TX_THRESHOLD,
                'usd': 500000  # $500K
            },
            'LTC': {
                'large_tx': self.LTC_LARGE_TX_THRESHOLD,
                'usd': 500000  # $500K
            }
        }

    def validate(self) -> bool:
        """Validate critical configuration."""
        errors = []

        if not self.DISCORD_WEBHOOK_URL:
            errors.append("DISCORD_WEBHOOK_URL is required")

        if self.POLL_INTERVAL_MINUTES < 5:
            errors.append("POLL_INTERVAL_MINUTES must be >= 5 to avoid rate limits")

        if errors:
            print("\n[ERROR] Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False

        print("[OK] Configuration validated successfully")
        return True

    def print_config(self):
        """Print current configuration (hiding sensitive values)."""
        print("\n=== Current Configuration ===")
        print(f"Discord Webhook: {'Set' if self.DISCORD_WEBHOOK_URL else 'NOT SET'}")
        print(f"Notification Time: {self.NOTIFICATION_TIME} {self.NOTIFICATION_TIMEZONE}")
        print(f"Poll Interval: {self.POLL_INTERVAL_MINUTES} minutes")
        print(f"BlockCypher API Key: {'Set' if self.BLOCKCYPHER_API_KEY else 'Not set (using free tier)'}")
        print(f"\nThresholds:")
        print(f"  BTC: {self.BTC_LARGE_TX_THRESHOLD} BTC")
        print(f"  DOGE: {self.DOGE_LARGE_TX_THRESHOLD:,.0f} DOGE")
        print(f"  LTC: {self.LTC_LARGE_TX_THRESHOLD} LTC")
        print(f"\nDatabase: {self.DATABASE_PATH}")
        print(f"Data Directory: {self.DATA_DIR}")
        print("=" * 30 + "\n")


if __name__ == "__main__":
    print("=== Testing Configuration ===\n")

    config = Config()
    config.print_config()

    print("Validating configuration...")
    is_valid = config.validate()

    if is_valid:
        print("\n[OK] Configuration is valid and ready to use")
    else:
        print("\n[ERROR] Please fix configuration errors before running")

    print("\nThresholds dict:")
    thresholds = config.get_thresholds()
    for coin, limits in thresholds.items():
        print(f"  {coin}: {limits}")
