"""
Wallet address parser for reading top 100 holder lists.
"""
import re
from typing import List, Dict
from pathlib import Path


class WalletParser:
    """Parse wallet addresses from BitInfoCharts scraped txt files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def parse_bitcoin_wallets(self) -> List[Dict[str, str]]:
        """Parse Bitcoin wallet addresses from txt file."""
        return self._parse_wallet_file("top_100_bitcoin_wallets.txt", "BTC")

    def parse_dogecoin_wallets(self) -> List[Dict[str, str]]:
        """Parse Dogecoin wallet addresses from txt file."""
        return self._parse_wallet_file("top_100_dogecoin_wallets.txt", "DOGE")

    def parse_litecoin_wallets(self) -> List[Dict[str, str]]:
        """Parse Litecoin wallet addresses from txt file."""
        return self._parse_wallet_file("top_100_litecoin_wallets.txt", "LTC")

    def parse_all_wallets(self) -> Dict[str, List[Dict[str, str]]]:
        """Parse all wallet files and return organized by coin type."""
        return {
            "BTC": self.parse_bitcoin_wallets(),
            "DOGE": self.parse_dogecoin_wallets(),
            "LTC": self.parse_litecoin_wallets()
        }

    def _parse_wallet_file(self, filename: str, coin_type: str) -> List[Dict[str, str]]:
        """
        Parse a wallet file and extract address information.

        Returns list of dicts with: rank, address, balance, percentage
        """
        file_path = self.data_dir / filename
        wallets = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Pattern to match lines like:
            # 1. 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo | 248,598 BTC | 1.25%
            # or with rank numbers like:
            # 8→1. 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo | 248,598 BTC | 1.25%

            pattern = r'(\d+)\.?\s+([A-Za-z0-9]+)\s+\|\s+([\d,]+(?:\.\d+)?)\s+(?:BTC|DOGE|LTC)\s+\|\s+([\d.]+)%'

            for line in content.split('\n'):
                # Remove line number prefix if exists (like "8→")
                line = re.sub(r'^\s*\d+→', '', line)

                match = re.search(pattern, line)
                if match:
                    rank = int(match.group(1))
                    address = match.group(2)
                    balance = match.group(3).replace(',', '')
                    percentage = match.group(4)

                    wallets.append({
                        'rank': rank,
                        'address': address,
                        'balance': balance,
                        'percentage': percentage,
                        'coin_type': coin_type
                    })

            print(f"[OK] Parsed {len(wallets)} {coin_type} wallet addresses")
            return wallets

        except FileNotFoundError:
            print(f"[ERROR] {filename} not found in {self.data_dir}")
            return []
        except Exception as e:
            print(f"[ERROR] Error parsing {filename}: {e}")
            return []


if __name__ == "__main__":
    # Test the parser
    parser = WalletParser(data_dir="../data")

    print("\n=== Testing Wallet Parser ===\n")

    btc_wallets = parser.parse_bitcoin_wallets()
    print(f"Bitcoin wallets: {len(btc_wallets)}")
    if btc_wallets:
        print(f"  Example: Rank #{btc_wallets[0]['rank']} - {btc_wallets[0]['address'][:20]}...")

    doge_wallets = parser.parse_dogecoin_wallets()
    print(f"Dogecoin wallets: {len(doge_wallets)}")
    if doge_wallets:
        print(f"  Example: Rank #{doge_wallets[0]['rank']} - {doge_wallets[0]['address'][:20]}...")

    ltc_wallets = parser.parse_litecoin_wallets()
    print(f"Litecoin wallets: {len(ltc_wallets)}")
    if ltc_wallets:
        print(f"  Example: Rank #{ltc_wallets[0]['rank']} - {ltc_wallets[0]['address'][:20]}...")

    print(f"\nTotal wallets to monitor: {len(btc_wallets) + len(doge_wallets) + len(ltc_wallets)}")
