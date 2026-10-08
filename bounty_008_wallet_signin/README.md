# Bounty #8: Wallet Sign-In Regression Suite

**Reward:** 1 USDG  
**Deadline:** 2026-10-14T09:54:30.000Z  
**Category:** Security

## Objective
Create a local test service and black-box regression suite for wallet sign-in using nonce-bound personal_sign messages.

## Requirements
- Local test service with generated test wallets
- Model: origin, chain ID, expiry, concurrent verification, session issuance
- **20+ adversarial cases** including:
  - Nonce replay
  - Wrong signer
  - Substituted origin
  - Expiration boundary
  - Malformed signature
  - Concurrent verification (only one may succeed)
- **2 intentionally vulnerable implementations** that suite rejects
- Executable runner
- Threat-model notes
- No real credentials or production attacks

## Deliverables
- Test service (Python)
- Regression suite (20+ cases)
- Vulnerable implementations (2)
- Runner script
- Threat model document
