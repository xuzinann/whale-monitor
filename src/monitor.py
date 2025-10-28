"""
Whale transaction monitor - core monitoring logic.
Polls blockchain APIs and detects new whale transactions.
"""
import time
from typing import List, Dict, Optional
from datetime import datetime

from wallet_parser import WalletParser
from blockchain_api import BlockchainAPIClient
from database import WhaleDatabase
from exchange_db import ExchangeDatabase


class WhaleMonitor:
    """Monitor whale wallets for new transactions."""

    def __init__(self, api_key: Optional[str] = None):
        print("=== Initializing Whale Monitor ===\n")

        # Initialize components
        self.parser = WalletParser(data_dir="../data")
        self.api_client = BlockchainAPIClient(api_key=api_key)
        self.database = WhaleDatabase(db_path="../data/whale_monitor.db")
        self.exchange_db = ExchangeDatabase(data_dir="../data")

        # Load wallet addresses
        self.wallets = self.parser.parse_all_wallets()
        total_wallets = sum(len(wallets) for wallets in self.wallets.values())
        print(f"\n[OK] Loaded {total_wallets} whale wallets to monitor\n")

        # Statistics
        self.stats = {
            'total_checks': 0,
            'new_transactions': 0,
            'api_errors': 0,
            'last_check_time': None
        }

    def check_wallet(self, wallet: Dict, coin_type: str) -> List[Dict]:
        """
        Check a single wallet for new transactions.

        Args:
            wallet: Wallet dict with address, rank, etc.
            coin_type: 'BTC', 'DOGE', or 'LTC'

        Returns:
            List of new transactions
        """
        address = wallet['address']
        rank = wallet['rank']

        # Get last seen block height from database
        last_block = self.database.get_wallet_last_block(address, coin_type)

        # Fetch transactions since last check
        try:
            if last_block == 0:
                # First time checking this wallet - only get latest transaction
                transactions = self.api_client.get_address_transactions(address, coin_type, limit=1)
            else:
                # Get transactions since last block
                transactions = self.api_client.get_latest_transactions(address, coin_type, since_block=last_block)

            if not transactions:
                return []

            # Process each transaction
            new_txs = []
            current_price = self.api_client.get_price(coin_type)

            for tx in transactions:
                processed_tx = self._process_transaction(tx, address, rank, coin_type, current_price)
                if processed_tx:
                    new_txs.append(processed_tx)

                    # Add to database
                    if self.database.add_transaction(processed_tx):
                        self.stats['new_transactions'] += 1

                    # Update last seen block
                    if tx.get('block_height', 0) > last_block:
                        self.database.update_wallet_tracking(address, coin_type, tx['block_height'], rank)

            return new_txs

        except Exception as e:
            print(f"[ERROR] Failed to check wallet {address[:20]}...: {e}")
            self.stats['api_errors'] += 1
            return []

    def _process_transaction(self, tx: Dict, wallet_address: str, wallet_rank: int,
                            coin_type: str, current_price: Optional[float]) -> Optional[Dict]:
        """Process a raw transaction and extract relevant information."""

        # Determine transaction direction and amount
        is_outgoing = False
        amount_native = 0

        # Check inputs to see if this wallet is sending
        for inp in tx.get('inputs', []):
            for addr in inp.get('addresses', []):
                if addr == wallet_address:
                    is_outgoing = True
                    # Sum up the amounts
                    amount_native += inp.get('output_value', 0) / 1e8

        # If not outgoing, it's incoming - sum outputs to this wallet
        if not is_outgoing:
            for out in tx.get('outputs', []):
                for addr in out.get('addresses', []):
                    if addr == wallet_address:
                        amount_native += out.get('value', 0) / 1e8

        # If no amount, skip
        if amount_native == 0:
            return None

        # Get all from/to addresses
        from_addresses = []
        to_addresses = []

        for inp in tx.get('inputs', []):
            from_addresses.extend(inp.get('addresses', []))

        for out in tx.get('outputs', []):
            to_addresses.extend(out.get('addresses', []))

        # Check if exchange-related
        is_exchange_related = False
        exchange_name = None

        # Check if any address is an exchange
        all_addresses = set(from_addresses + to_addresses)
        for addr in all_addresses:
            if addr != wallet_address:
                if self.exchange_db.is_exchange_address(addr, coin_type):
                    is_exchange_related = True
                    exchange_name = self.exchange_db.get_exchange_name(addr, coin_type)
                    break

        # Calculate USD value
        amount_usd = None
        if current_price:
            amount_usd = amount_native * current_price

        return {
            'tx_hash': tx['hash'],
            'coin_type': coin_type,
            'wallet_address': wallet_address,
            'wallet_rank': wallet_rank,
            'amount_native': amount_native,
            'amount_usd': amount_usd,
            'from_addresses': from_addresses,
            'to_addresses': to_addresses,
            'is_outgoing': is_outgoing,
            'is_exchange_related': is_exchange_related,
            'exchange_name': exchange_name,
            'block_height': tx.get('block_height', -1),
            'confirmed': tx.get('confirmed', False),
            'tx_timestamp': tx.get('received', datetime.now().isoformat())
        }

    def check_all_wallets(self):
        """Check all monitored wallets for new transactions."""
        print(f"\n=== Starting wallet check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

        start_time = time.time()
        total_new_txs = 0

        for coin_type, wallets in self.wallets.items():
            print(f"Checking {len(wallets)} {coin_type} wallets...")

            for wallet in wallets:
                new_txs = self.check_wallet(wallet, coin_type)
                total_new_txs += len(new_txs)

                if new_txs:
                    for tx in new_txs:
                        direction = "sent" if tx['is_outgoing'] else "received"
                        exchange_info = f" ({tx['exchange_name']})" if tx['is_exchange_related'] else ""
                        usd_value = f"${tx['amount_usd']:,.0f}" if tx['amount_usd'] else "?"

                        print(f"  [NEW] Whale #{tx['wallet_rank']} {direction} "
                              f"{tx['amount_native']:.2f} {coin_type} ({usd_value}){exchange_info}")

        elapsed = time.time() - start_time
        self.stats['total_checks'] += 1
        self.stats['last_check_time'] = datetime.now()

        print(f"\nCheck completed in {elapsed:.1f}s")
        print(f"New transactions found: {total_new_txs}")
        print(f"Total checks: {self.stats['total_checks']}")
        print(f"Total new transactions: {self.stats['new_transactions']}")

        return total_new_txs

    def run_continuous(self, interval_minutes: int = 10):
        """
        Run continuous monitoring loop.

        Args:
            interval_minutes: Minutes between checks (default: 10)
        """
        print(f"\n[OK] Starting continuous monitoring (checking every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                self.check_all_wallets()

                # Sleep until next check
                sleep_seconds = interval_minutes * 60
                next_check = datetime.now().timestamp() + sleep_seconds
                next_check_time = datetime.fromtimestamp(next_check).strftime('%H:%M:%S')

                print(f"\nSleeping until next check at {next_check_time}...\n")
                time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            print("\n\n[OK] Monitoring stopped by user")
            self.cleanup()

    def run_once(self):
        """Run a single check of all wallets."""
        self.check_all_wallets()
        self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        print("\n=== Cleaning up ===")
        self.database.close()
        print("[OK] Monitor shutdown complete")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("         WHALE MONITOR - Transaction Tracker")
    print("=" * 60)

    # Check for API key argument
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(f"\nUsing API key: {api_key[:10]}...")

    # Initialize monitor
    monitor = WhaleMonitor(api_key=api_key)

    # Run single check for testing
    print("\n[INFO] Running single check (use run_continuous() for ongoing monitoring)\n")
    monitor.run_once()
