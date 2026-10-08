# Bounty #6: Escrow Invariant Harness

**Reward:** 1 USDG
**Deadline:** 2026-10-14T09:54:30.000Z
**Category:** Smart Contracts

## Objective
Build Foundry test harness for escrow contract invariants.

## Requirements
- Test invariant: balance always equals deposits minus releases
- Test invariant: only payer can release
- Test invariant: no partial release without approval
- Fuzz testing with random deposit/release sequences
- Use Foundry invariant testing
- 100% branch coverage

## Deliverables
- Foundry test suite
- Escrow contract (if not provided)
- Invariant tests
- Coverage report
