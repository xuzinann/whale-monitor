#!/usr/bin/env python3
"""
Quick diagnostic script to check whale monitor status
"""
import sys
sys.path.insert(0, 'src')

from database import WhaleDatabase
from datetime import datetime, timedelta

print("=" * 60)
print("WHALE MONITOR DIAGNOSTIC CHECK")
print("=" * 60 + "\n")

db = WhaleDatabase(db_path="data/whale_monitor.db")

# Check wallet tracking
print("1. WALLET TRACKING STATUS")
print("-" * 40)
cursor = db.conn.cursor()

cursor.execute("""
    SELECT coin_type, COUNT(*) as wallet_count,
           MIN(last_checked) as oldest_check,
           MAX(last_checked) as newest_check
    FROM wallet_tracking
    GROUP BY coin_type
""")

tracking = cursor.fetchall()
if tracking:
    for row in tracking:
        print(f"{row['coin_type']}:")
        print(f"  Wallets tracked: {row['wallet_count']}")
        print(f"  Last check: {row['newest_check']}")
else:
    print("  [WARNING] No wallets being tracked yet!")
    print("  This might mean the monitor hasn't started checking wallets.")

# Check transactions
print("\n2. TRANSACTION HISTORY")
print("-" * 40)

cursor.execute("""
    SELECT coin_type, COUNT(*) as tx_count,
           MIN(detected_at) as first_tx,
           MAX(detected_at) as latest_tx
    FROM transactions
    GROUP BY coin_type
""")

txs = cursor.fetchall()
if txs:
    for row in txs:
        print(f"{row['coin_type']}:")
        print(f"  Transactions: {row['tx_count']}")
        print(f"  First detected: {row['first_tx']}")
        print(f"  Latest: {row['latest_tx']}")
else:
    print("  [INFO] No transactions detected yet.")
    print("  This is NORMAL if:")
    print("    - Monitor just started recently")
    print("    - Whales haven't moved coins since monitoring began")

# Check recent activity (last 24 hours)
print("\n3. RECENT ACTIVITY (Last 24 Hours)")
print("-" * 40)

recent = db.get_recent_transactions(coin_type=None, hours=24, limit=100)
if recent:
    print(f"  Total transactions: {len(recent)}")

    for coin_type in ['BTC', 'DOGE', 'LTC']:
        coin_txs = [tx for tx in recent if tx['coin_type'] == coin_type]
        if coin_txs:
            print(f"\n  {coin_type}: {len(coin_txs)} transactions")
            for tx in coin_txs[:3]:  # Show first 3
                direction = "sent" if tx['is_outgoing'] else "received"
                amount = tx['amount_native']
                print(f"    - Whale #{tx['wallet_rank']} {direction} {amount:.2f} {coin_type}")
else:
    print("  No transactions in last 24 hours")

# Check monitoring stats
print("\n4. SYSTEM STATUS")
print("-" * 40)

cursor.execute("SELECT COUNT(*) as total FROM transactions")
total_txs = cursor.fetchone()['total']

cursor.execute("SELECT COUNT(*) as total FROM wallet_tracking")
total_wallets = cursor.fetchone()['total']

print(f"  Total wallets tracked: {total_wallets}/300")
print(f"  Total transactions recorded: {total_txs}")

if total_wallets == 0:
    print("\n  [ERROR] No wallets tracked! Monitor may not be running properly.")
elif total_wallets < 300:
    print(f"\n  [INFO] Only {total_wallets} wallets tracked so far.")
    print("  Monitor may still be doing initial checks.")

# Check for errors
print("\n5. RECOMMENDATIONS")
print("-" * 40)

if total_txs == 0 and total_wallets > 0:
    print("  ✓ Monitor is running and tracking wallets")
    print("  ✓ No transactions detected yet - this is NORMAL")
    print("  → Whales are inactive (common for HODLers)")
    print("  → Keep monitoring, alerts will come when they move coins")
elif total_txs > 0:
    print("  ✓ Monitor is working correctly!")
    print(f"  ✓ {total_txs} transactions have been detected")
    print("  → Check Discord for digest notifications")
else:
    print("  ⚠ Monitor may not be running")
    print("  → Check if main.py process is active")
    print("  → Review console output for errors")

db.close()

print("\n" + "=" * 60)
print("DIAGNOSTIC CHECK COMPLETE")
print("=" * 60)
