#!/usr/bin/env python3
"""
Ledger Reconciliation Tool - Bounty #15
Compare off-chain ledger balances with on-chain balances.
"""

import sqlite3
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class DiscrepancyType(Enum):
    MISSING_ONCHAIN = "missing_onchain"
    MISSING_OFFCHAIN = "missing_offchain"
    BALANCE_MISMATCH = "balance_mismatch"
    TOKEN_NOT_FOUND = "token_not_found"


@dataclass
class Discrepancy:
    address: str
    token: str
    offchain_balance: int
    onchain_balance: int
    discrepancy_type: DiscrepancyType
    difference: int
    timestamp: float


@dataclass
class ReconciliationResult:
    total_checked: int
    matched: int
    discrepancies: List[Discrepancy]
    duration: float


class LedgerReconciliation:
    """
    Reconcile off-chain ledger with on-chain balances.
    
    Features:
    - Compare balances across multiple tokens/addresses
    - Detect discrepancies with classification
    - Generate detailed reports
    - SQLite-backed storage
    """
    
    def __init__(self, db_path: str = "ledger.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Off-chain ledger
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offchain_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                token TEXT NOT NULL,
                balance INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                
                UNIQUE(address, token)
            )
        """)
        
        # On-chain balances (cached)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onchain_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                token TEXT NOT NULL,
                balance INTEGER NOT NULL,
                block_number INTEGER,
                fetched_at REAL NOT NULL,
                
                UNIQUE(address, token)
            )
        """)
        
        # Reconciliation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reconciliation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                token TEXT NOT NULL,
                offchain_balance INTEGER NOT NULL,
                onchain_balance INTEGER NOT NULL,
                discrepancy_type TEXT NOT NULL,
                difference INTEGER NOT NULL,
                reconciled_at REAL NOT NULL
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_offchain_addr ON offchain_ledger(address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_onchain_addr ON onchain_balances(address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON reconciliation_history(reconciled_at)")
        
        conn.commit()
        conn.close()
    
    def update_offchain_ledger(self, address: str, token: str, balance: int):
        """Update off-chain ledger balance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO offchain_ledger (address, token, balance, updated_at)
            VALUES (?, ?, ?, ?)
        """, (address.lower(), token.lower(), balance, time.time()))
        
        conn.commit()
        conn.close()
    
    def update_onchain_balance(self, address: str, token: str, balance: int, block_number: int = 0):
        """Update cached on-chain balance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO onchain_balances 
            (address, token, balance, block_number, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (address.lower(), token.lower(), balance, block_number, time.time()))
        
        conn.commit()
        conn.close()
    
    def get_offchain_balance(self, address: str, token: str) -> Optional[int]:
        """Get off-chain balance for address/token."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT balance FROM offchain_ledger
            WHERE address = ? AND token = ?
        """, (address.lower(), token.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def get_onchain_balance(self, address: str, token: str) -> Optional[int]:
        """Get cached on-chain balance for address/token."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT balance FROM onchain_balances
            WHERE address = ? AND token = ?
        """, (address.lower(), token.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def reconcile(self, tokens: Optional[List[str]] = None) -> ReconciliationResult:
        """
        Perform reconciliation between off-chain and on-chain balances.
        
        Args:
            tokens: Optional list of tokens to check (all if None)
        
        Returns:
            ReconciliationResult with matches and discrepancies
        """
        start_time = time.time()
        discrepancies = []
        matched = 0
        total = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all off-chain entries
        if tokens:
            placeholders = ','.join('?' * len(tokens))
            cursor.execute(f"""
                SELECT address, token, balance FROM offchain_ledger
                WHERE token IN ({placeholders})
            """, [t.lower() for t in tokens])
        else:
            cursor.execute("SELECT address, token, balance FROM offchain_ledger")
        
        offchain_entries = cursor.fetchall()
        
        for address, token, offchain_balance in offchain_entries:
            total += 1
            
            # Get on-chain balance
            cursor.execute("""
                SELECT balance FROM onchain_balances
                WHERE address = ? AND token = ?
            """, (address, token))
            
            row = cursor.fetchone()
            onchain_balance = row[0] if row else None
            
            if onchain_balance is None:
                # Missing on-chain
                discrepancies.append(Discrepancy(
                    address=address,
                    token=token,
                    offchain_balance=offchain_balance,
                    onchain_balance=0,
                    discrepancy_type=DiscrepancyType.MISSING_ONCHAIN,
                    difference=offchain_balance,
                    timestamp=time.time()
                ))
            elif offchain_balance != onchain_balance:
                # Balance mismatch
                discrepancies.append(Discrepancy(
                    address=address,
                    token=token,
                    offchain_balance=offchain_balance,
                    onchain_balance=onchain_balance,
                    discrepancy_type=DiscrepancyType.BALANCE_MISMATCH,
                    difference=abs(offchain_balance - onchain_balance),
                    timestamp=time.time()
                ))
            else:
                matched += 1
        
        # Check for on-chain entries missing in off-chain
        if tokens:
            placeholders = ','.join('?' * len(tokens))
            cursor.execute(f"""
                SELECT address, token, balance FROM onchain_balances
                WHERE token IN ({placeholders})
            """, [t.lower() for t in tokens])
        else:
            cursor.execute("SELECT address, token, balance FROM onchain_balances")
        
        onchain_entries = cursor.fetchall()
        
        for address, token, onchain_balance in onchain_entries:
            cursor.execute("""
                SELECT balance FROM offchain_ledger
                WHERE address = ? AND token = ?
            """, (address, token))
            
            if not cursor.fetchone():
                total += 1
                discrepancies.append(Discrepancy(
                    address=address,
                    token=token,
                    offchain_balance=0,
                    onchain_balance=onchain_balance,
                    discrepancy_type=DiscrepancyType.MISSING_OFFCHAIN,
                    difference=onchain_balance,
                    timestamp=time.time()
                ))
        
        conn.close()
        
        # Store discrepancies
        self._store_discrepancies(discrepancies)
        
        duration = time.time() - start_time
        
        return ReconciliationResult(
            total_checked=total,
            matched=matched,
            discrepancies=discrepancies,
            duration=duration
        )
    
    def _store_discrepancies(self, discrepancies: List[Discrepancy]):
        """Store discrepancies in history."""
        if not discrepancies:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for d in discrepancies:
            cursor.execute("""
                INSERT INTO reconciliation_history
                (address, token, offchain_balance, onchain_balance, discrepancy_type, difference, reconciled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (d.address, d.token, d.offchain_balance, d.onchain_balance,
                  d.discrepancy_type.value, d.difference, d.timestamp))
        
        conn.commit()
        conn.close()
    
    def generate_report(self, result: ReconciliationResult) -> str:
        """Generate human-readable reconciliation report."""
        lines = [
            "=" * 70,
            "LEDGER RECONCILIATION REPORT",
            "=" * 70,
            "",
            f"Total Checked:     {result.total_checked}",
            f"Matched:           {result.matched}",
            f"Discrepancies:     {len(result.discrepancies)}",
            f"Duration:          {result.duration:.3f}s",
            "",
        ]
        
        if result.discrepancies:
            lines.append("=" * 70)
            lines.append("DISCREPANCIES")
            lines.append("=" * 70)
            lines.append("")
            
            for i, d in enumerate(result.discrepancies, 1):
                lines.extend([
                    f"#{i} {d.discrepancy_type.value.upper()}",
                    f"  Address:  {d.address}",
                    f"  Token:    {d.token}",
                    f"  Off-chain: {d.offchain_balance}",
                    f"  On-chain:  {d.onchain_balance}",
                    f"  Diff:     {d.difference}",
                    "",
                ])
        else:
            lines.append("✓ All balances matched!")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reconciliation statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM offchain_ledger")
        offchain_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM onchain_balances")
        onchain_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reconciliation_history")
        history_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT token) FROM offchain_ledger")
        token_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'offchain_entries': offchain_count,
            'onchain_entries': onchain_count,
            'reconciliation_runs': history_count,
            'unique_tokens': token_count
        }


def simulate_data(reconciliation: LedgerReconciliation, n_entries: int = 100,
                  discrepancy_rate: float = 0.1):
    """Simulate ledger data with some discrepancies."""
    import random
    
    random.seed(20261008)
    
    tokens = ['USDC', 'USDT', 'DAI', 'WETH', 'WBTC']
    
    for i in range(n_entries):
        address = f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        token = random.choice(tokens)
        balance = random.randint(0, 1000000) * 10**6  # Use 10^6 instead of 10^18
        
        # Update off-chain
        reconciliation.update_offchain_ledger(address, token, balance)
        
        # Update on-chain (with some discrepancies)
        if random.random() < discrepancy_rate:
            # Create discrepancy
            discrepancy_type = random.choice(['missing', 'mismatch'])
            
            if discrepancy_type == 'missing':
                # Don't add to on-chain
                pass
            else:
                # Different balance
                diff = random.randint(1, 1000) * 10**6
                onchain_balance = balance + diff if random.random() > 0.5 else max(0, balance - diff)
                reconciliation.update_onchain_balance(address, token, onchain_balance, 12345678)
        else:
            # Matching balance
            reconciliation.update_onchain_balance(address, token, balance, 12345678)


def main():
    print("=== Ledger Reconciliation Tool ===\n")
    
    import os
    db_path = "/tmp/test_ledger.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    reconciliation = LedgerReconciliation(db_path)
    
    print("Generating test data...\n")
    simulate_data(reconciliation, n_entries=100, discrepancy_rate=0.15)
    
    stats = reconciliation.get_stats()
    print(f"Off-chain entries: {stats['offchain_entries']}")
    print(f"On-chain entries:  {stats['onchain_entries']}")
    print(f"Unique tokens:     {stats['unique_tokens']}")
    
    print("\nRunning reconciliation...\n")
    result = reconciliation.reconcile()
    
    report = reconciliation.generate_report(result)
    print(report)
    
    print("\n✓ Ledger reconciliation complete")
    
    os.remove(db_path)


if __name__ == '__main__':
    main()
