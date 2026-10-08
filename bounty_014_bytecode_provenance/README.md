# Bounty #14: Bytecode Provenance

**Reward:** 1 USDG
**Deadline:** 2026-10-14T09:54:30.000Z
**Category:** Development

## Objective
Given an arbitrary initcode, find all candidate sources: solc versions, optimizer runs, viaIR flags.

## Requirements
- Match bytecode against known compiler configurations
- Handle deployed code vs initcode
- Test with multiple Solidity versions (0.4.x - 0.8.x)
- Report: compiler version, optimizer runs, viaIR
- 50+ bytecode samples with known provenance
- Matching confidence score
- One-command runner

## Deliverables
- Provenance matcher
- Test samples
- Results report
