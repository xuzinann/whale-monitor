"""
Discord notification formatter and sender.
Creates formatted whale activity digests and sends to Discord.
"""
from typing import List, Dict, Optional
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed


class DiscordNotifier:
    """Handle Discord webhook notifications."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

        # Emoji mapping for different coins
        self.coin_emoji = {
            'BTC': ':large_blue_circle:',  # 🔷
            'DOGE': ':yellow_circle:',      # 🟡
            'LTC': ':white_circle:'         # ⚪
        }

    def _format_amount(self, amount: float, decimals: int = 2) -> str:
        """Format large numbers with commas."""
        return f"{amount:,.{decimals}f}"

    def _format_usd(self, amount: float) -> str:
        """Format USD amount."""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        else:
            return f"${amount:.0f}"

    def send_daily_digest(self, date: str, summaries: Dict[str, Dict]) -> bool:
        """
        Send daily whale activity digest.

        Args:
            date: Date string (YYYY-MM-DD)
            summaries: Dict with BTC/DOGE/LTC summary stats

        Returns:
            True if sent successfully
        """
        webhook = DiscordWebhook(url=self.webhook_url)

        # Main title
        title = f"🐋 DAILY WHALE DIGEST - {date}"
        description = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Add summary for each coin
        for coin_type in ['BTC', 'DOGE', 'LTC']:
            if coin_type not in summaries:
                continue

            stats = summaries[coin_type]
            if stats['transaction_count'] == 0:
                continue

            emoji = self.coin_emoji.get(coin_type, '')
            description += f"{emoji} **{coin_type} Whales**\n"
            description += "━━━━━━━━━━━━━━━━━━━━\n"

            # Significant moves
            sig_count = stats.get('significant_count', 0)
            total_volume_usd = stats.get('total_volume_usd', 0)

            if sig_count > 0:
                description += f"🚨 **{sig_count} significant moves** | "
                description += f"**{self._format_usd(total_volume_usd)} total volume**\n\n"

            # Exchange flow
            exchange_inflow = stats.get('exchange_inflow', 0)
            exchange_outflow = stats.get('exchange_outflow', 0)
            net_flow = stats.get('exchange_net_flow', 0)

            if exchange_inflow > 0 or exchange_outflow > 0:
                flow_direction = "net inflow" if net_flow > 0 else "net outflow"
                description += f"📊 **Exchange flow:** {self._format_amount(abs(net_flow))} {coin_type} {flow_direction}\n"

            # Most active wallets
            most_active = stats.get('most_active', [])
            if most_active:
                top_whale = most_active[0]
                rank = top_whale.get('wallet_rank', '?')
                tx_count = top_whale.get('tx_count', 0)
                description += f"⚡ **Most active:** Whale #{rank} ({tx_count} transactions)\n"

            description += "\n"

        # Add footer
        description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        description += "_Generated with Claude Code_"

        # Create embed
        embed = DiscordEmbed(
            title=title,
            description=description,
            color='03b2f8'  # Blue color
        )

        embed.set_timestamp()

        webhook.add_embed(embed)

        try:
            response = webhook.execute()
            if response.status_code == 200:
                print(f"[OK] Daily digest sent to Discord")
                return True
            else:
                print(f"[ERROR] Discord webhook failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to send Discord notification: {e}")
            return False

    def send_significant_transaction_alert(self, tx: Dict, analysis: Dict) -> bool:
        """
        Send alert for a significant transaction.

        Args:
            tx: Transaction dict
            analysis: Analysis result from SignificanceAnalyzer
        """
        webhook = DiscordWebhook(url=self.webhook_url)

        coin_type = tx['coin_type']
        emoji = self.coin_emoji.get(coin_type, '')

        # Create title
        direction = "sent" if tx['is_outgoing'] else "received"
        title = f"{emoji} Whale #{tx.get('wallet_rank', '?')} {direction} {coin_type}"

        # Create description
        amount_native = tx['amount_native']
        amount_usd = tx.get('amount_usd')

        description = f"**Amount:** {self._format_amount(amount_native)} {coin_type}"
        if amount_usd:
            description += f" ({self._format_usd(amount_usd)})\n"
        else:
            description += "\n"

        # Exchange info
        if tx.get('is_exchange_related'):
            exchange_name = tx.get('exchange_name', 'Unknown Exchange')
            description += f"**Exchange:** {exchange_name}\n"

        # Tags
        if analysis.get('tags'):
            tags = ' '.join(f"`{tag}`" for tag in analysis['tags'])
            description += f"**Tags:** {tags}\n"

        # Pattern
        if analysis.get('pattern'):
            description += f"**Pattern:** {analysis['pattern'].title()}\n"

        # Transaction hash (shortened)
        tx_hash = tx['tx_hash']
        description += f"\n**TX:** `{tx_hash[:16]}...`"

        # Create embed
        color_map = {
            10: 'ff0000',  # Red - highest
            9: 'ff3300',
            8: 'ff6600',
            7: 'ff9900',
            6: 'ffcc00',  # Orange/Yellow
            5: 'ffff00',
            4: '00ff00',  # Green
            3: '00cc00',
            2: '009900',
            1: '006600'
        }

        score = analysis.get('significance_score', 0)
        color = color_map.get(score, '808080')  # Gray default

        embed = DiscordEmbed(
            title=title,
            description=description,
            color=color
        )

        embed.set_footer(text=f"Significance: {score}/10")
        embed.set_timestamp()

        webhook.add_embed(embed)

        try:
            response = webhook.execute()
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Failed to send transaction alert: {e}")
            return False

    def send_test_message(self) -> bool:
        """Send a test message to verify webhook is working."""
        webhook = DiscordWebhook(
            url=self.webhook_url,
            content="🐋 Whale Monitor initialized and ready!"
        )

        try:
            response = webhook.execute()
            if response.status_code == 200:
                print("[OK] Test message sent successfully")
                return True
            else:
                print(f"[ERROR] Test message failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to send test message: {e}")
            return False


if __name__ == "__main__":
    import os

    print("=== Testing Discord Notifier ===\n")

    # Try to load webhook from environment
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("[WARNING] DISCORD_WEBHOOK_URL not set in environment")
        print("Set it with: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print("\nUsing dummy URL for testing (will fail to send)")
        webhook_url = "https://discord.com/api/webhooks/test/test"

    notifier = DiscordNotifier(webhook_url)

    # Test digest
    print("Creating sample daily digest...\n")

    sample_summaries = {
        'BTC': {
            'transaction_count': 15,
            'total_volume_native': 1250.5,
            'total_volume_usd': 142000000,
            'significant_count': 7,
            'exchange_inflow': 850,
            'exchange_outflow': 200,
            'exchange_net_flow': 650,
            'most_active': [
                {'wallet_rank': 12, 'tx_count': 8, 'total_volume': 500}
            ]
        },
        'DOGE': {
            'transaction_count': 23,
            'total_volume_native': 500000000,
            'total_volume_usd': 8500000,
            'significant_count': 12,
            'exchange_inflow': 250000000,
            'exchange_outflow': 100000000,
            'exchange_net_flow': 150000000,
            'most_active': [
                {'wallet_rank': 3, 'tx_count': 15, 'total_volume': 200000000}
            ]
        },
        'LTC': {
            'transaction_count': 8,
            'total_volume_native': 15000,
            'total_volume_usd': 1500000,
            'significant_count': 3,
            'exchange_inflow': 10000,
            'exchange_outflow': 5000,
            'exchange_net_flow': -5000,
            'most_active': [
                {'wallet_rank': 5, 'tx_count': 4, 'total_volume': 8000}
            ]
        }
    }

    print("Sample digest created (not sent unless webhook is valid)\n")
    print("Daily digest format:")
    print("-" * 50)

    # Show what the message would look like
    date = datetime.now().strftime('%Y-%m-%d')
    print(f"[WHALE] DAILY WHALE DIGEST - {date}")
    print("=" * 50)
    print("\n[BTC] BTC Whales")
    print("-" * 30)
    print("[!] 7 significant moves | $142.0M total volume")
    print("[>] Exchange flow: 650.00 BTC net inflow")
    print("[*] Most active: Whale #12 (8 transactions)")
    print("\nTest completed!")
