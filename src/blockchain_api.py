"""
Blockchain API client for fetching transaction data.
Supports BTC, DOGE, and LTC using BlockCypher API.
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime


class BlockchainAPIClient:
    """Client for interacting with blockchain APIs."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.blockcypher.com/v1"
        self.session = requests.Session()

        # Rate limiting: BlockCypher free tier allows 3 requests/sec, 200 requests/hour
        self.last_request_time = 0
        self.min_request_interval = 0.35  # 350ms between requests (~ 2.8 req/sec)

        # Price cache (refresh every 5 minutes)
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_duration = 300  # 5 minutes

    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with error handling."""
        self._rate_limit()

        try:
            if params is None:
                params = {}

            if self.api_key:
                params['token'] = self.api_key

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"[WARNING] Rate limit exceeded, waiting 60s...")
                time.sleep(60)
                return None
            print(f"[ERROR] HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return None
        except ValueError as e:
            print(f"[ERROR] Invalid JSON response: {e}")
            return None

    def get_address_transactions(self, address: str, coin_type: str, limit: int = 50) -> List[Dict]:
        """
        Fetch recent transactions for an address.

        Args:
            address: Wallet address
            coin_type: 'BTC', 'DOGE', or 'LTC'
            limit: Maximum number of transactions to fetch

        Returns:
            List of transaction dictionaries
        """
        coin_map = {
            'BTC': 'btc',
            'DOGE': 'doge',
            'LTC': 'ltc'
        }

        coin = coin_map.get(coin_type)
        if not coin:
            print(f"[ERROR] Unsupported coin type: {coin_type}")
            return []

        url = f"{self.base_url}/{coin}/main/addrs/{address}/full"
        params = {'limit': min(limit, 50)}  # BlockCypher max is 50

        data = self._make_request(url, params)
        if not data:
            return []

        transactions = []
        for tx in data.get('txs', []):
            transactions.append({
                'hash': tx['hash'],
                'block_height': tx.get('block_height', 0),
                'confirmed': tx.get('confirmed') is not None,
                'received': tx.get('received', ''),
                'total': tx.get('total', 0),
                'fees': tx.get('fees', 0),
                'inputs': tx.get('inputs', []),
                'outputs': tx.get('outputs', []),
            })

        return transactions

    def get_address_balance(self, address: str, coin_type: str) -> Optional[float]:
        """Get current balance for an address."""
        coin_map = {'BTC': 'btc', 'DOGE': 'doge', 'LTC': 'ltc'}
        coin = coin_map.get(coin_type)

        if not coin:
            return None

        url = f"{self.base_url}/{coin}/main/addrs/{address}/balance"
        data = self._make_request(url)

        if not data:
            return None

        # Convert satoshis to main unit
        balance = data.get('balance', 0)
        return balance / 1e8

    def get_latest_transactions(self, address: str, coin_type: str, since_block: Optional[int] = None) -> List[Dict]:
        """
        Get transactions since a specific block height.

        Args:
            address: Wallet address
            coin_type: Coin type
            since_block: Only return transactions after this block height

        Returns:
            List of new transactions
        """
        all_txs = self.get_address_transactions(address, coin_type, limit=50)

        if since_block is None:
            return all_txs

        # Filter transactions by block height
        new_txs = [tx for tx in all_txs if tx.get('block_height', 0) > since_block]
        return new_txs

    def get_price(self, coin_type: str) -> Optional[float]:
        """
        Get current USD price for a coin.
        Uses CoinGecko API (free, no key needed).
        """
        # Check cache first
        now = time.time()
        if coin_type in self.price_cache:
            if now - self.price_cache_time[coin_type] < self.price_cache_duration:
                return self.price_cache[coin_type]

        coin_map = {
            'BTC': 'bitcoin',
            'DOGE': 'dogecoin',
            'LTC': 'litecoin'
        }

        coin_id = coin_map.get(coin_type)
        if not coin_id:
            return None

        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            price = data.get(coin_id, {}).get('usd')
            if price:
                # Update cache
                self.price_cache[coin_type] = price
                self.price_cache_time[coin_type] = now

            return price

        except Exception as e:
            print(f"[ERROR] Failed to fetch price for {coin_type}: {e}")
            # Return cached value if available, even if expired
            return self.price_cache.get(coin_type)

    def get_transaction_details(self, tx_hash: str, coin_type: str) -> Optional[Dict]:
        """Get detailed information about a specific transaction."""
        coin_map = {'BTC': 'btc', 'DOGE': 'doge', 'LTC': 'ltc'}
        coin = coin_map.get(coin_type)

        if not coin:
            return None

        url = f"{self.base_url}/{coin}/main/txs/{tx_hash}"
        return self._make_request(url)


if __name__ == "__main__":
    # Test the API client
    print("=== Testing Blockchain API Client ===\n")

    client = BlockchainAPIClient()

    # Test BTC price
    print("Fetching current prices...")
    btc_price = client.get_price('BTC')
    doge_price = client.get_price('DOGE')
    ltc_price = client.get_price('LTC')

    if btc_price:
        print(f"BTC: ${btc_price:,.2f}")
    if doge_price:
        print(f"DOGE: ${doge_price:.4f}")
    if ltc_price:
        print(f"LTC: ${ltc_price:.2f}")

    print("\nFetching sample transaction data...")

    # Test with a known BTC address (smaller whale for faster testing)
    test_address = "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h"
    print(f"\nQuerying BTC address: {test_address[:20]}...")

    balance = client.get_address_balance(test_address, 'BTC')
    if balance:
        print(f"Balance: {balance:,.2f} BTC")

    txs = client.get_address_transactions(test_address, 'BTC', limit=5)
    print(f"Recent transactions: {len(txs)}")

    if txs:
        latest = txs[0]
        print(f"Latest TX: {latest['hash'][:20]}...")
        print(f"  Block: {latest.get('block_height', 'unconfirmed')}")
        print(f"  Confirmed: {latest.get('confirmed', False)}")
