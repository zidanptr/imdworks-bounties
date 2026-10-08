# Bounty #7: Reorg-Safe Indexer

**Reward:** 1 USDG
**Deadline:** 2026-10-14T09:54:30.000Z
**Category:** Development

## Objective
Build indexer that handles chain reorganizations gracefully.

## Requirements
- Track block confirmations
- Mark events as confirmed after N blocks
- Handle reorg detection and event rollback
- Test with simulated reorgs
- Query confirmed events only
- SQLite-backed storage

## Deliverables
- Reorg-safe indexer service
- Block tracker
- Event storage with confirmation status
- Reorg simulation tests
