# Bounty #9: USDG Decimal Parser

**Reward:** 1 USDG  
**Deadline:** 2026-10-14T09:54:30.000Z  
**Category:** Data

## Objective
Write a small six-decimal token amount parser and formatter using integer arithmetic.

## Requirements
- Define explicit grammar for user input
- Separate canonical display representation
- Handle: leading zeros, huge amounts, Unicode lookalikes, exponents, signs, whitespace, excess precision
- **100,000+ seeded generated cases**
- **30 hand-selected edge cases**
- Round-trip correctness for accepted values
- Reject ambiguous/lossy inputs
- Cross-check against reference implementation
- **3 floating-point counterexamples**
- Machine-readable results
- No silent rounding

## Deliverables
- Parser code (Python)
- Test generator
- Results (seeded, reproducible)
- Edge case table
- Floating-point counterexamples
- One-command runner
