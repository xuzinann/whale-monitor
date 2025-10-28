"""
Transaction significance analyzer.
Identifies significant whale movements and patterns.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database import WhaleDatabase


class SignificanceAnalyzer:
    """Analyze transactions to identify significant movements."""

    def __init__(self, db: WhaleDatabase, thresholds: Optional[Dict] = None):
        self.db = db

        # Default thresholds for significance
        self.thresholds = thresholds or {
            'BTC': {'large_tx': 50, 'usd': 1000000},
            'DOGE': {'large_tx': 10000000, 'usd': 500000},
            'LTC': {'large_tx': 5000, 'usd': 500000}
        }

        # Thresholds for unusual activity
        self.unusual_activity_multiplier = 3.0  # 3x normal activity

    def is_large_transaction(self, tx: Dict) -> bool:
        """Check if transaction exceeds size threshold."""
        coin_type = tx['coin_type']
        amount_native = tx['amount_native']
        amount_usd = tx.get('amount_usd', 0)

        threshold = self.thresholds.get(coin_type, {})

        # Check native amount OR USD value
        if amount_native >= threshold.get('large_tx', float('inf')):
            return True

        if amount_usd and amount_usd >= threshold.get('usd', float('inf')):
            return True

        return False

    def is_exchange_transfer(self, tx: Dict) -> bool:
        """Check if transaction involves an exchange."""
        return tx.get('is_exchange_related', False)

    def is_unusual_activity(self, wallet_address: str, coin_type: str, hours: int = 24) -> bool:
        """
        Detect if a wallet is unusually active.

        Compare recent activity to historical average.
        """
        # Get recent transaction count
        recent_txs = self.db.get_recent_transactions(coin_type, hours=hours)
        wallet_recent = [tx for tx in recent_txs if tx['wallet_address'] == wallet_address]
        recent_count = len(wallet_recent)

        if recent_count == 0:
            return False

        # Get historical average (30-day lookback)
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as total_count,
                   JULIANDAY('now') - JULIANDAY(MIN(detected_at)) as days
            FROM transactions
            WHERE wallet_address = ? AND coin_type = ?
            AND detected_at > datetime('now', '-30 days')
        """, (wallet_address, coin_type))

        result = cursor.fetchone()
        if not result or result['days'] == 0:
            # Not enough history
            return False

        total_count = result['total_count']
        days = result['days']
        avg_daily = total_count / days

        # Calculate expected transactions in the time window
        expected_in_period = avg_daily * (hours / 24.0)

        # Unusual if current activity is > 3x normal
        return recent_count > (expected_in_period * self.unusual_activity_multiplier)

    def detect_accumulation_pattern(self, wallet_address: str, coin_type: str, days: int = 7) -> Optional[str]:
        """
        Detect if wallet is accumulating or distributing.

        Returns: 'accumulating', 'distributing', or None
        """
        cursor = self.db.conn.cursor()

        # Get net flow (incoming - outgoing)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN is_outgoing = 0 THEN amount_native ELSE 0 END) as inflow,
                SUM(CASE WHEN is_outgoing = 1 THEN amount_native ELSE 0 END) as outflow
            FROM transactions
            WHERE wallet_address = ? AND coin_type = ?
            AND detected_at > datetime('now', '-' || ? || ' days')
        """, (wallet_address, coin_type, days))

        result = cursor.fetchone()
        if not result:
            return None

        inflow = result['inflow'] or 0
        outflow = result['outflow'] or 0

        net_flow = inflow - outflow

        # Significant if net flow is > 10% of either direction
        threshold = max(inflow, outflow) * 0.1

        if abs(net_flow) < threshold:
            return None

        return 'accumulating' if net_flow > 0 else 'distributing'

    def analyze_transaction(self, tx: Dict) -> Dict:
        """
        Analyze a transaction for all significance factors.

        Returns dict with analysis results.
        """
        analysis = {
            'is_large': self.is_large_transaction(tx),
            'is_exchange': self.is_exchange_transfer(tx),
            'is_unusual': False,
            'pattern': None,
            'significance_score': 0,
            'tags': []
        }

        # Check unusual activity
        if tx.get('wallet_address'):
            analysis['is_unusual'] = self.is_unusual_activity(
                tx['wallet_address'],
                tx['coin_type'],
                hours=24
            )

            # Check accumulation pattern
            analysis['pattern'] = self.detect_accumulation_pattern(
                tx['wallet_address'],
                tx['coin_type'],
                days=7
            )

        # Calculate significance score (0-10)
        score = 0
        if analysis['is_large']:
            score += 4
            analysis['tags'].append('LARGE')

        if analysis['is_exchange']:
            score += 3
            analysis['tags'].append('EXCHANGE')

        if analysis['is_unusual']:
            score += 2
            analysis['tags'].append('UNUSUAL')

        if analysis['pattern']:
            score += 1
            analysis['tags'].append(analysis['pattern'].upper())

        analysis['significance_score'] = min(score, 10)

        return analysis

    def get_significant_transactions(self, coin_type: Optional[str] = None,
                                    hours: int = 24, min_score: int = 4) -> List[Dict]:
        """
        Get significant transactions from a time period.

        Args:
            coin_type: Filter by coin type (optional)
            hours: Time window
            min_score: Minimum significance score

        Returns:
            List of transactions with analysis
        """
        transactions = self.db.get_recent_transactions(coin_type, hours=hours, limit=1000)

        significant = []
        for tx in transactions:
            analysis = self.analyze_transaction(tx)
            if analysis['significance_score'] >= min_score:
                tx['analysis'] = analysis
                significant.append(tx)

        # Sort by significance score
        significant.sort(key=lambda x: x['analysis']['significance_score'], reverse=True)

        return significant

    def generate_summary_stats(self, coin_type: str, hours: int = 24) -> Dict:
        """
        Generate summary statistics for a time period.

        Returns dict with:
        - total_volume
        - transaction_count
        - exchange_flow
        - significant_moves
        - most_active_wallets
        """
        transactions = self.db.get_recent_transactions(coin_type, hours=hours, limit=10000)

        if not transactions:
            return {
                'total_volume_native': 0,
                'total_volume_usd': 0,
                'transaction_count': 0,
                'exchange_inflow': 0,
                'exchange_outflow': 0,
                'significant_count': 0,
                'most_active': []
            }

        # Calculate stats
        total_volume_native = sum(tx.get('amount_native', 0) for tx in transactions)
        total_volume_usd = sum(tx.get('amount_usd', 0) or 0 for tx in transactions)

        exchange_inflow = sum(
            tx.get('amount_native', 0)
            for tx in transactions
            if tx.get('is_exchange_related') and tx.get('is_outgoing')
        )

        exchange_outflow = sum(
            tx.get('amount_native', 0)
            for tx in transactions
            if tx.get('is_exchange_related') and not tx.get('is_outgoing')
        )

        # Count significant transactions
        significant_count = sum(
            1 for tx in transactions
            if self.is_large_transaction(tx) or self.is_exchange_transfer(tx)
        )

        # Get most active wallets
        most_active = self.db.get_most_active_wallets(coin_type, hours=hours, limit=5)

        return {
            'total_volume_native': total_volume_native,
            'total_volume_usd': total_volume_usd,
            'transaction_count': len(transactions),
            'exchange_inflow': exchange_inflow,
            'exchange_outflow': exchange_outflow,
            'exchange_net_flow': exchange_inflow - exchange_outflow,
            'significant_count': significant_count,
            'most_active': most_active
        }


if __name__ == "__main__":
    # Test the analyzer
    from blockchain_api import BlockchainAPIClient

    print("=== Testing Significance Analyzer ===\n")

    db = WhaleDatabase(db_path="../data/whale_monitor.db")
    analyzer = SignificanceAnalyzer(db)

    # Test with a sample transaction
    api_client = BlockchainAPIClient()

    test_tx = {
        'tx_hash': 'test123',
        'coin_type': 'BTC',
        'wallet_address': 'bc1qtest',
        'amount_native': 100,  # 100 BTC - should be large
        'amount_usd': 11000000,
        'is_exchange_related': True,
        'is_outgoing': True
    }

    analysis = analyzer.analyze_transaction(test_tx)
    print(f"Test transaction analysis:")
    print(f"  Significance score: {analysis['significance_score']}/10")
    print(f"  Tags: {', '.join(analysis['tags'])}")
    print(f"  Is large: {analysis['is_large']}")
    print(f"  Is exchange: {analysis['is_exchange']}")

    # Test summary stats
    print("\nBTC summary stats (last 24h):")
    stats = analyzer.generate_summary_stats('BTC', hours=24)
    print(f"  Transactions: {stats['transaction_count']}")
    print(f"  Total volume: {stats['total_volume_native']:.2f} BTC")
    if stats['total_volume_usd'] > 0:
        print(f"  Total volume USD: ${stats['total_volume_usd']:,.0f}")
    print(f"  Significant moves: {stats['significant_count']}")

    db.close()
