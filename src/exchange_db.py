"""
Exchange address database for identifying exchange-related transactions.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional


class ExchangeDatabase:
    """Manage and query exchange address database."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.exchange_file = self.data_dir / "exchange_addresses.json"
        self.exchanges = self._load_exchanges()

        # Create lookup dictionaries for fast checking
        self.btc_exchanges = {ex['address']: ex for ex in self.exchanges.get('BTC', [])}
        self.doge_exchanges = {ex['address']: ex for ex in self.exchanges.get('DOGE', [])}
        self.ltc_exchanges = {ex['address']: ex for ex in self.exchanges.get('LTC', [])}

    def _load_exchanges(self) -> Dict[str, List[Dict]]:
        """Load exchange addresses from JSON file."""
        try:
            with open(self.exchange_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[OK] Loaded exchange database:")
            print(f"  - BTC: {len(data.get('BTC', []))} exchange addresses")
            print(f"  - DOGE: {len(data.get('DOGE', []))} exchange addresses")
            print(f"  - LTC: {len(data.get('LTC', []))} exchange addresses")
            return data
        except FileNotFoundError:
            print(f"[WARNING] Exchange database not found at {self.exchange_file}")
            return {'BTC': [], 'DOGE': [], 'LTC': []}
        except Exception as e:
            print(f"[ERROR] Error loading exchange database: {e}")
            return {'BTC': [], 'DOGE': [], 'LTC': []}

    def is_exchange_address(self, address: str, coin_type: str) -> bool:
        """Check if an address belongs to an exchange."""
        lookup = {
            'BTC': self.btc_exchanges,
            'DOGE': self.doge_exchanges,
            'LTC': self.ltc_exchanges
        }
        return address in lookup.get(coin_type, {})

    def get_exchange_info(self, address: str, coin_type: str) -> Optional[Dict]:
        """Get exchange information for an address."""
        lookup = {
            'BTC': self.btc_exchanges,
            'DOGE': self.doge_exchanges,
            'LTC': self.ltc_exchanges
        }
        return lookup.get(coin_type, {}).get(address)

    def get_exchange_name(self, address: str, coin_type: str) -> Optional[str]:
        """Get exchange name for an address."""
        info = self.get_exchange_info(address, coin_type)
        return info['exchange'] if info else None

    def add_exchange_address(self, address: str, coin_type: str, exchange: str, wallet_type: str = "unknown"):
        """Add a new exchange address to the database."""
        if coin_type not in self.exchanges:
            self.exchanges[coin_type] = []

        new_entry = {
            "address": address,
            "exchange": exchange,
            "wallet_type": wallet_type
        }

        self.exchanges[coin_type].append(new_entry)

        # Update lookup dictionaries
        if coin_type == 'BTC':
            self.btc_exchanges[address] = new_entry
        elif coin_type == 'DOGE':
            self.doge_exchanges[address] = new_entry
        elif coin_type == 'LTC':
            self.ltc_exchanges[address] = new_entry

    def save_exchanges(self):
        """Save exchange database to JSON file."""
        try:
            with open(self.exchange_file, 'w', encoding='utf-8') as f:
                json.dump(self.exchanges, f, indent=2)
            print(f"[OK] Exchange database saved to {self.exchange_file}")
        except Exception as e:
            print(f"[ERROR] Error saving exchange database: {e}")


if __name__ == "__main__":
    # Test the exchange database
    db = ExchangeDatabase(data_dir="../data")

    print("\n=== Testing Exchange Database ===\n")

    # Test BTC address
    btc_address = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"
    if db.is_exchange_address(btc_address, "BTC"):
        info = db.get_exchange_info(btc_address, "BTC")
        print(f"BTC Address: {btc_address[:20]}...")
        print(f"  Exchange: {info['exchange']}")
        print(f"  Type: {info['wallet_type']}\n")

    # Test DOGE address
    doge_address = "DEgDVFa2DoW1533dxeDVdTxQFhMzs1pMke"
    if db.is_exchange_address(doge_address, "DOGE"):
        info = db.get_exchange_info(doge_address, "DOGE")
        print(f"DOGE Address: {doge_address[:20]}...")
        print(f"  Exchange: {info['exchange']}")
        print(f"  Type: {info['wallet_type']}\n")

    # Test unknown address
    unknown = "1ABC123456789"
    print(f"Unknown address: {unknown}")
    print(f"  Is exchange: {db.is_exchange_address(unknown, 'BTC')}")
