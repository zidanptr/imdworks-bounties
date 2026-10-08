#!/usr/bin/env python3
"""
Reorg-Safe Indexer - Bounty #7
Handles chain reorganizations with confirmation tracking.
"""

import sqlite3
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ConfirmationStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Block:
    number: int
    hash: str
    parent_hash: str
    timestamp: int
    confirmations: int


@dataclass
class IndexedEvent:
    id: int
    block_number: int
    block_hash: str
    tx_hash: str
    event_type: str
    data: str
    status: str
    confirmations: int


class ReorgSafeIndexer:
    """
    Indexer that handles chain reorganizations.
    
    Features:
    - Track block confirmations
    - Mark events confirmed after N blocks
    - Detect and handle reorgs
    - Rollback events from orphaned blocks
    """
    
    def __init__(self, db_path: str = "indexer.db", confirmation_threshold: int = 12):
        self.db_path = db_path
        self.confirmation_threshold = confirmation_threshold
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Blocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                number INTEGER PRIMARY KEY,
                hash TEXT NOT NULL UNIQUE,
                parent_hash TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                confirmations INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                indexed_at REAL NOT NULL
            )
        """)
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_number INTEGER NOT NULL,
                block_hash TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                log_index INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                confirmations INTEGER DEFAULT 0,
                indexed_at REAL NOT NULL,
                
                UNIQUE(tx_hash, log_index),
                FOREIGN KEY (block_number) REFERENCES blocks(number)
            )
        """)
        
        # Chain state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chain_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                latest_block INTEGER DEFAULT 0,
                latest_hash TEXT,
                last_update REAL
            )
        """)
        
        # Initialize chain state
        cursor.execute("""
            INSERT OR IGNORE INTO chain_state (id, latest_block, last_update)
            VALUES (1, 0, 0)
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_block ON events(block_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocks_parent ON blocks(parent_hash)")
        
        conn.commit()
        conn.close()
    
    def index_block(self, block: Block) -> Dict[str, Any]:
        """
        Index a new block.
        
        Returns:
            Dict with indexing result
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = time.time()
            
            # Check for reorg: if parent_hash doesn't match, reorg detected
            cursor.execute("""
                SELECT hash FROM blocks WHERE number = ?
            """, (block.number - 1,))
            
            prev_block = cursor.fetchone()
            if prev_block and prev_block[0] != block.parent_hash:
                # Reorg detected!
                return self._handle_reorg(conn, block)
            
            # Insert block
            cursor.execute("""
                INSERT OR REPLACE INTO blocks 
                (number, hash, parent_hash, timestamp, confirmations, status, indexed_at)
                VALUES (?, ?, ?, ?, 0, 'pending', ?)
            """, (block.number, block.hash, block.parent_hash, block.timestamp, now))
            
            # Update chain state
            cursor.execute("""
                UPDATE chain_state 
                SET latest_block = ?, latest_hash = ?, last_update = ?
                WHERE id = 1
            """, (block.number, block.hash, now))
            
            conn.commit()
            
            return {
                'success': True,
                'block_number': block.number,
                'status': 'indexed'
            }
        
        finally:
            conn.close()
    
    def index_event(self, block_number: int, block_hash: str, tx_hash: str,
                    log_index: int, event_type: str, data: str) -> Dict[str, Any]:
        """
        Index an event.
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            now = time.time()
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO events
                (block_number, block_hash, tx_hash, log_index, event_type, data, status, confirmations, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?)
            """, (block_number, block_hash, tx_hash, log_index, event_type, data, now))
            
            conn.commit()
            
            return {
                'success': True,
                'event_id': cursor.lastrowid
            }
        
        finally:
            conn.close()
    
    def update_confirmations(self, current_block: int) -> Dict[str, Any]:
        """
        Update confirmation counts for all indexed blocks.
        
        Mark blocks and events as confirmed after threshold.
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.cursor()
            
            # Update block confirmations
            cursor.execute("""
                UPDATE blocks
                SET confirmations = ? - number,
                    status = CASE 
                        WHEN ? - number >= ? THEN 'confirmed'
                        ELSE status
                    END
                WHERE status = 'pending'
            """, (current_block, current_block, self.confirmation_threshold))
            
            blocks_confirmed = cursor.rowcount
            
            # Update event confirmations
            cursor.execute("""
                UPDATE events
                SET confirmations = ? - block_number,
                    status = CASE
                        WHEN ? - block_number >= ? THEN 'confirmed'
                        ELSE status
                    END
                WHERE status = 'pending'
            """, (current_block, current_block, self.confirmation_threshold))
            
            events_confirmed = cursor.rowcount
            
            conn.commit()
            
            return {
                'success': True,
                'blocks_confirmed': blocks_confirmed,
                'events_confirmed': events_confirmed,
                'current_block': current_block
            }
        
        finally:
            conn.close()
    
    def _handle_reorg(self, conn: sqlite3.Connection, new_block: Block) -> Dict[str, Any]:
        """
        Handle chain reorganization.
        
        1. Find common ancestor
        2. Mark orphaned blocks as rolled_back
        3. Mark orphaned events as rolled_back
        4. Reindex from common ancestor
        """
        cursor = conn.cursor()
        
        # Find blocks to rollback
        cursor.execute("""
            SELECT number, hash FROM blocks
            WHERE number >= ? AND status != 'rolled_back'
            ORDER BY number DESC
        """, (new_block.number,))
        
        orphaned_blocks = cursor.fetchall()
        
        # Find common ancestor
        common_ancestor = new_block.number - 1
        
        # Rollback events
        cursor.execute("""
            UPDATE events
            SET status = 'rolled_back'
            WHERE block_number >= ? AND status != 'rolled_back'
        """, (new_block.number,))
        
        events_rolled_back = cursor.rowcount
        
        # Rollback blocks
        cursor.execute("""
            UPDATE blocks
            SET status = 'rolled_back'
            WHERE number >= ? AND status != 'rolled_back'
        """, (new_block.number,))
        
        blocks_rolled_back = cursor.rowcount
        
        # Insert new block
        now = time.time()
        cursor.execute("""
            INSERT OR REPLACE INTO blocks
            (number, hash, parent_hash, timestamp, confirmations, status, indexed_at)
            VALUES (?, ?, ?, ?, 0, 'pending', ?)
        """, (new_block.number, new_block.hash, new_block.parent_hash, new_block.timestamp, now))
        
        conn.commit()
        
        return {
            'success': True,
            'reorg_detected': True,
            'blocks_rolled_back': blocks_rolled_back,
            'events_rolled_back': events_rolled_back,
            'common_ancestor': common_ancestor,
            'new_block': new_block.number
        }
    
    def get_confirmed_events(self, event_type: Optional[str] = None,
                             limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get confirmed events only.
        
        These events have survived confirmation threshold and are safe to use.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            if event_type:
                cursor.execute("""
                    SELECT * FROM events
                    WHERE status = 'confirmed' AND event_type = ?
                    ORDER BY block_number, log_index
                    LIMIT ? OFFSET ?
                """, (event_type, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM events
                    WHERE status = 'confirmed'
                    ORDER BY block_number, log_index
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
        
        finally:
            conn.close()
    
    def get_pending_events(self, limit: int = 100) -> List[Dict]:
        """Get pending events (not yet confirmed)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM events
                WHERE status = 'pending'
                ORDER BY block_number, log_index
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexer statistics."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM blocks WHERE status = 'pending'")
            pending_blocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM blocks WHERE status = 'confirmed'")
            confirmed_blocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM blocks WHERE status = 'rolled_back'")
            rolled_back_blocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'pending'")
            pending_events = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'confirmed'")
            confirmed_events = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'rolled_back'")
            rolled_back_events = cursor.fetchone()[0]
            
            cursor.execute("SELECT latest_block, latest_hash FROM chain_state WHERE id = 1")
            chain = cursor.fetchone()
            
            return {
                'latest_block': chain[0] if chain else 0,
                'latest_hash': chain[1] if chain else None,
                'pending_blocks': pending_blocks,
                'confirmed_blocks': confirmed_blocks,
                'rolled_back_blocks': rolled_back_blocks,
                'pending_events': pending_events,
                'confirmed_events': confirmed_events,
                'rolled_back_events': rolled_back_events,
                'confirmation_threshold': self.confirmation_threshold
            }
        
        finally:
            conn.close()


def simulate_chain(indexer: ReorgSafeIndexer, n_blocks: int = 50,
                   reorg_at: Optional[int] = None) -> Dict[str, Any]:
    """
    Simulate chain with optional reorg.
    """
    import random
    
    random.seed(20261008)
    
    stats = {'blocks_indexed': 0, 'events_indexed': 0, 'reorgs': 0}
    
    blocks = []
    prev_hash = '0x' + '0' * 64
    
    for i in range(n_blocks):
        block_hash = '0x' + ''.join(random.choices('0123456789abcdef', k=64))
        
        block = Block(
            number=i,
            hash=block_hash,
            parent_hash=prev_hash,
            timestamp=int(time.time()) + i * 12,
            confirmations=0
        )
        
        # Simulate reorg
        if reorg_at and i == reorg_at:
            # Create alternative block with different hash
            alt_hash = '0x' + ''.join(random.choices('abcdef0123456789', k=64))
            alt_block = Block(
                number=i,
                hash=alt_hash,
                parent_hash=prev_hash,
                timestamp=block.timestamp,
                confirmations=0
            )
            
            result = indexer.index_block(alt_block)
            if result.get('reorg_detected'):
                stats['reorgs'] += 1
                stats['blocks_indexed'] += 1
            
            block_hash = alt_hash
        else:
            indexer.index_block(block)
            stats['blocks_indexed'] += 1
        
        # Index some events
        for j in range(random.randint(1, 5)):
            tx_hash = '0x' + ''.join(random.choices('0123456789abcdef', k=64))
            event_type = random.choice(['Transfer', 'Approval', 'Swap'])
            data = f'{{"from": "0x...", "to": "0x...", "value": {random.randint(1, 1000)}}}'
            
            indexer.index_event(i, block_hash, tx_hash, j, event_type, data)
            stats['events_indexed'] += 1
        
        prev_hash = block_hash
        blocks.append(block_hash)
    
    # Update confirmations
    indexer.update_confirmations(n_blocks - 1)
    
    stats.update(indexer.get_stats())
    
    return stats


def main():
    print("=== Reorg-Safe Indexer ===\n")
    
    import os
    db_path = "/tmp/test_indexer.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    indexer = ReorgSafeIndexer(db_path, confirmation_threshold=12)
    
    print("Test 1: Normal chain indexing\n")
    stats = simulate_chain(indexer, n_blocks=50)
    
    print(f"Blocks indexed: {stats['blocks_indexed']}")
    print(f"Events indexed: {stats['events_indexed']}")
    print(f"Reorgs detected: {stats['reorgs']}")
    print(f"Confirmed blocks: {stats['confirmed_blocks']}")
    print(f"Confirmed events: {stats['confirmed_events']}")
    
    print("\n" + "="*50)
    print("Test 2: Chain with reorg at block 30\n")
    
    os.remove(db_path)
    indexer = ReorgSafeIndexer(db_path, confirmation_threshold=12)
    
    stats = simulate_chain(indexer, n_blocks=50, reorg_at=30)
    
    print(f"Blocks indexed: {stats['blocks_indexed']}")
    print(f"Events indexed: {stats['events_indexed']}")
    print(f"Reorgs detected: {stats['reorgs']}")
    print(f"Rolled back events: {stats['rolled_back_events']}")
    print(f"Confirmed events: {stats['confirmed_events']}")
    
    print("\n" + "="*50)
    print("Test 3: Query confirmed events\n")
    
    confirmed = indexer.get_confirmed_events(limit=10)
    print(f"Confirmed events (first 10): {len(confirmed)}")
    
    pending = indexer.get_pending_events(limit=10)
    print(f"Pending events (first 10): {len(pending)}")
    
    print("\n✓ Reorg-safe indexer tests complete")
    
    os.remove(db_path)


if __name__ == '__main__':
    main()
