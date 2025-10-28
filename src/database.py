"""
Database module for storing whale transaction data.
Uses SQLite for simplicity and portability.
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json


class WhaleDatabase:
    """Manage whale transaction data storage."""

    def __init__(self, db_path: str = "data/whale_monitor.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        print(f"[OK] Connected to database: {self.db_path}")

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Transactions table (30-day retention)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT NOT NULL,
                coin_type TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                wallet_rank INTEGER,
                amount_native REAL,
                amount_usd REAL,
                from_addresses TEXT,
                to_addresses TEXT,
                is_outgoing BOOLEAN,
                is_exchange_related BOOLEAN,
                exchange_name TEXT,
                block_height INTEGER,
                confirmed BOOLEAN,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tx_timestamp TEXT,
                UNIQUE(tx_hash, wallet_address)
            )
        """)

        # Wallet tracking table (last seen block height for each wallet)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                coin_type TEXT NOT NULL,
                wallet_rank INTEGER,
                last_block_height INTEGER DEFAULT 0,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_count INTEGER DEFAULT 0,
                UNIQUE(wallet_address, coin_type)
            )
        """)

        # Monthly summaries (permanent storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                coin_type TEXT NOT NULL,
                total_volume_native REAL,
                total_volume_usd REAL,
                transaction_count INTEGER,
                exchange_inflow_native REAL,
                exchange_outflow_native REAL,
                most_active_wallets TEXT,
                significant_moves_count INTEGER,
                summary_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(month, coin_type)
            )
        """)

        # Whale activity statistics (for unusual activity detection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whale_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                coin_type TEXT NOT NULL,
                avg_daily_transactions REAL DEFAULT 0,
                last_7d_transactions INTEGER DEFAULT 0,
                last_30d_volume REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_address, coin_type)
            )
        """)

        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_coin_date ON transactions(coin_type, detected_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_wallet ON transactions(wallet_address, coin_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_exchange ON transactions(is_exchange_related, detected_at)")

        self.conn.commit()
        print("[OK] Database tables created/verified")

    def add_transaction(self, tx_data: Dict) -> bool:
        """Add a new transaction to the database."""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO transactions (
                    tx_hash, coin_type, wallet_address, wallet_rank,
                    amount_native, amount_usd, from_addresses, to_addresses,
                    is_outgoing, is_exchange_related, exchange_name,
                    block_height, confirmed, tx_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx_data['tx_hash'],
                tx_data['coin_type'],
                tx_data['wallet_address'],
                tx_data.get('wallet_rank'),
                tx_data['amount_native'],
                tx_data.get('amount_usd'),
                json.dumps(tx_data.get('from_addresses', [])),
                json.dumps(tx_data.get('to_addresses', [])),
                tx_data['is_outgoing'],
                tx_data.get('is_exchange_related', False),
                tx_data.get('exchange_name'),
                tx_data.get('block_height'),
                tx_data.get('confirmed', False),
                tx_data.get('tx_timestamp')
            ))

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            # Transaction already exists
            return False
        except Exception as e:
            print(f"[ERROR] Failed to add transaction: {e}")
            return False

    def update_wallet_tracking(self, wallet_address: str, coin_type: str,
                               block_height: int, wallet_rank: int = None):
        """Update the last seen block height for a wallet."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO wallet_tracking (wallet_address, coin_type, wallet_rank, last_block_height, transaction_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(wallet_address, coin_type) DO UPDATE SET
                last_block_height = MAX(last_block_height, ?),
                last_checked = CURRENT_TIMESTAMP,
                transaction_count = transaction_count + 1,
                wallet_rank = COALESCE(?, wallet_rank)
        """, (wallet_address, coin_type, wallet_rank, block_height, block_height, wallet_rank))

        self.conn.commit()

    def get_wallet_last_block(self, wallet_address: str, coin_type: str) -> int:
        """Get the last seen block height for a wallet."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT last_block_height FROM wallet_tracking
            WHERE wallet_address = ? AND coin_type = ?
        """, (wallet_address, coin_type))

        result = cursor.fetchone()
        return result['last_block_height'] if result else 0

    def get_recent_transactions(self, coin_type: str = None, hours: int = 24,
                                limit: int = 100) -> List[Dict]:
        """Get recent transactions, optionally filtered by coin type."""
        cursor = self.conn.cursor()

        since = datetime.now() - timedelta(hours=hours)

        if coin_type:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE coin_type = ? AND detected_at > ?
                ORDER BY detected_at DESC
                LIMIT ?
            """, (coin_type, since, limit))
        else:
            cursor.execute("""
                SELECT * FROM transactions
                WHERE detected_at > ?
                ORDER BY detected_at DESC
                LIMIT ?
            """, (since, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_todays_transactions(self, coin_type: str = None) -> List[Dict]:
        """Get all transactions from today."""
        return self.get_recent_transactions(coin_type, hours=24, limit=1000)

    def get_exchange_flow(self, coin_type: str, hours: int = 24) -> Tuple[float, float]:
        """
        Calculate net exchange flow (inflow - outflow) for a time period.

        Returns: (inflow, outflow) in native currency
        """
        cursor = self.conn.cursor()
        since = datetime.now() - timedelta(hours=hours)

        # Inflow: transactions TO exchanges (is_outgoing = True, is_exchange_related = True)
        cursor.execute("""
            SELECT COALESCE(SUM(amount_native), 0) as total
            FROM transactions
            WHERE coin_type = ? AND detected_at > ?
            AND is_exchange_related = 1 AND is_outgoing = 1
        """, (coin_type, since))

        inflow = cursor.fetchone()['total']

        # Outflow: transactions FROM exchanges (is_outgoing = False, is_exchange_related = True)
        cursor.execute("""
            SELECT COALESCE(SUM(amount_native), 0) as total
            FROM transactions
            WHERE coin_type = ? AND detected_at > ?
            AND is_exchange_related = 1 AND is_outgoing = 0
        """, (coin_type, since))

        outflow = cursor.fetchone()['total']

        return (inflow, outflow)

    def get_most_active_wallets(self, coin_type: str, hours: int = 24, limit: int = 5) -> List[Dict]:
        """Get most active wallets in a time period."""
        cursor = self.conn.cursor()
        since = datetime.now() - timedelta(hours=hours)

        cursor.execute("""
            SELECT wallet_address, wallet_rank, COUNT(*) as tx_count,
                   SUM(amount_native) as total_volume
            FROM transactions
            WHERE coin_type = ? AND detected_at > ?
            GROUP BY wallet_address
            ORDER BY tx_count DESC
            LIMIT ?
        """, (coin_type, since, limit))

        return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_transactions(self, days: int = 30):
        """Delete transactions older than specified days."""
        cursor = self.conn.cursor()
        cutoff = datetime.now() - timedelta(days=days)

        cursor.execute("""
            DELETE FROM transactions WHERE detected_at < ?
        """, (cutoff,))

        deleted = cursor.rowcount
        self.conn.commit()

        if deleted > 0:
            print(f"[OK] Cleaned up {deleted} old transactions")

    def create_monthly_summary(self, month: str, coin_type: str):
        """Create a monthly summary for archival."""
        cursor = self.conn.cursor()

        # Get transactions for the month
        cursor.execute("""
            SELECT
                COUNT(*) as tx_count,
                SUM(amount_native) as total_volume_native,
                SUM(amount_usd) as total_volume_usd,
                SUM(CASE WHEN is_exchange_related = 1 AND is_outgoing = 1 THEN amount_native ELSE 0 END) as exchange_inflow,
                SUM(CASE WHEN is_exchange_related = 1 AND is_outgoing = 0 THEN amount_native ELSE 0 END) as exchange_outflow,
                SUM(CASE WHEN amount_usd > 100000 THEN 1 ELSE 0 END) as significant_count
            FROM transactions
            WHERE coin_type = ? AND strftime('%Y-%m', detected_at) = ?
        """, (coin_type, month))

        stats = dict(cursor.fetchone())

        # Get most active wallets
        cursor.execute("""
            SELECT wallet_address, wallet_rank, COUNT(*) as tx_count
            FROM transactions
            WHERE coin_type = ? AND strftime('%Y-%m', detected_at) = ?
            GROUP BY wallet_address
            ORDER BY tx_count DESC
            LIMIT 10
        """, (coin_type, month))

        active_wallets = [dict(row) for row in cursor.fetchall()]

        # Insert summary
        cursor.execute("""
            INSERT OR REPLACE INTO monthly_summaries (
                month, coin_type, total_volume_native, total_volume_usd,
                transaction_count, exchange_inflow_native, exchange_outflow_native,
                most_active_wallets, significant_moves_count, summary_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            month, coin_type,
            stats['total_volume_native'],
            stats['total_volume_usd'],
            stats['tx_count'],
            stats['exchange_inflow'],
            stats['exchange_outflow'],
            json.dumps(active_wallets),
            stats['significant_count'],
            json.dumps(stats)
        ))

        self.conn.commit()
        print(f"[OK] Created monthly summary for {month} ({coin_type})")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("[OK] Database connection closed")


if __name__ == "__main__":
    # Test the database
    print("=== Testing Database ===\n")

    db = WhaleDatabase(db_path="../data/whale_monitor.db")

    # Test adding a transaction
    test_tx = {
        'tx_hash': 'test_hash_12345',
        'coin_type': 'BTC',
        'wallet_address': 'bc1qtest123',
        'wallet_rank': 1,
        'amount_native': 100.5,
        'amount_usd': 11000000,
        'from_addresses': ['bc1qfrom1', 'bc1qfrom2'],
        'to_addresses': ['bc1qto1'],
        'is_outgoing': True,
        'is_exchange_related': True,
        'exchange_name': 'Binance',
        'block_height': 850000,
        'confirmed': True,
        'tx_timestamp': datetime.now().isoformat()
    }

    result = db.add_transaction(test_tx)
    print(f"Transaction added: {result}")

    # Test wallet tracking
    db.update_wallet_tracking('bc1qtest123', 'BTC', 850000, wallet_rank=1)
    last_block = db.get_wallet_last_block('bc1qtest123', 'BTC')
    print(f"Last block height: {last_block}")

    # Test querying recent transactions
    recent = db.get_recent_transactions('BTC', hours=24, limit=10)
    print(f"Recent transactions: {len(recent)}")

    db.close()
