# Wallet Sign-In Regression Suite - Bounty #8 Submission

**Bounty:** #8 - Construct an adversarial wallet sign-in regression suite  
**Reward:** 1 USDG  
**Deadline:** 2026-10-14T09:54:30.000Z  
**Category:** Security

---

## Executive Summary

Delivered a complete local test service and black-box regression suite for wallet sign-in using nonce-bound `personal_sign` messages. **20 adversarial test cases** covering replay attacks, wrong signer, origin substitution, expiration boundaries, malformed signatures, and concurrent verification. Includes **2 intentionally vulnerable implementations** demonstrating real-world security flaws.

**All 20 tests pass (100%).**

---

## Deliverables

### 1. Test Service (`wallet_signin_service.py`)

Secure wallet sign-in service implementing:

**Security Properties:**
- ✅ Nonce is single-use (replay protection)
- ✅ Signature bound to origin (CSRF protection)
- ✅ Signature bound to chain ID (cross-chain protection)
- ✅ Challenge expires (time window protection)
- ✅ Concurrent verification fails second attempt (race condition protection)

**API:**
```python
service = WalletSignInService()

# Create challenge
challenge_id, message = service.create_challenge(
    wallet="0x...",
    origin="https://app.example.com",
    chain_id=1
)

# Verify signature
session = service.verify_signature(
    challenge_id=challenge_id,
    signature="0x..."
)
```

### 2. Regression Suite (`test_suite.py`)

**20 adversarial test cases** across 7 categories:

| # | Test Case | Category | Expected |
|---|-----------|----------|----------|
| 1 | Valid signature | Valid | SUCCESS |
| 2 | Replay same challenge | Nonce replay | REJECTED |
| 3 | Replay nonce collision | Nonce replay | REJECTED |
| 4 | Replay expired challenge | Nonce replay | REJECTED |
| 5 | Wrong signer - different wallet | Wrong signer | REJECTED |
| 6 | Wrong signer - random key | Wrong signer | REJECTED |
| 7 | Wrong signer - empty signature | Wrong signer | REJECTED |
| 8 | Origin substitution - cross-site | Origin substitution | REJECTED |
| 9 | Origin missing - uses challenge | Origin substitution | SUCCESS |
| 10 | Origin protocol downgrade | Origin substitution | REJECTED |
| 11 | Expiry - before boundary | Expiration boundary | SUCCESS |
| 12 | Expiry - after boundary | Expiration boundary | REJECTED |
| 13 | Session expiry rejected | Expiration boundary | REJECTED |
| 14 | Session valid access | Expiration boundary | SUCCESS |
| 15 | Malformed - truncated signature | Malformed signature | REJECTED |
| 16 | Malformed - extended signature | Malformed signature | REJECTED |
| 17 | Malformed - invalid hex | Malformed signature | REJECTED |
| 18 | Malformed - wrong v value | Malformed signature | REJECTED |
| 19 | Concurrent - one success only | Concurrent verification | ONE_SUCCESS |
| 20 | Concurrent - different challenges | Concurrent verification | BOTH_SUCCESS |

**Results:**
```
Passed: 20/20 (100.0%)
Failed: 0/20
```

### 3. Vulnerable Implementations

#### V1: No Nonce Tracking (`vulnerable_v1_no_nonce.py`)

**Vulnerability:** Does not track used challenges, allows signature replay.

```python
# User signs once
challenge_id, message = service.create_challenge(wallet)
signature = sign_message(privkey, message)

# First verification succeeds
session1 = service.verify_signature(challenge_id, signature)  # ✓

# REPLAY ATTACK - Same signature works again!
session2 = service.verify_signature(challenge_id, signature)  # ✗ VULNERABLE
```

**Attack Scenario:**
1. User signs challenge on legitimate site
2. Attacker intercepts signature
3. Attacker replays signature to create unauthorized sessions

**Fixed by:** Nonce tracking in secure implementation.

#### V2: No Origin Binding (`vulnerable_v2_no_origin.py`)

**Vulnerability:** Origin not included in signed message, allows CSRF.

```python
# Legitimate sign-in on app.example.com
challenge_id, message = service.create_challenge(
    wallet, 
    origin="https://app.example.com"
)
# Message does NOT include origin!

# User signs
signature = sign_message(privkey, message)

# Attacker uses signature on evil.com
session = service.verify_signature(
    challenge_id, 
    signature,
    provided_origin="https://evil.com"  # ✗ VULNERABLE - works!
)
```

**Attack Scenario:**
1. User visits `evil.com` which loads hidden iframe to `app.example.com`
2. User signs challenge (message doesn't specify origin)
3. `evil.com` uses signature to authenticate on user's behalf

**Fixed by:** Including origin in signed message in secure implementation.

### 4. Runner Script (`run_tests.sh`)

```bash
./run_tests.sh
```

Runs full suite + demonstrates vulnerable implementations.

---

## Threat Model

### Attack Surface

| Attack Vector | Mitigation |
|---------------|------------|
| **Replay attacks** | Single-use nonce, challenge marked as used |
| **CSRF** | Origin bound to signed message |
| **Cross-chain attacks** | Chain ID bound to signed message |
| **Timing attacks** | Challenge expiration (5 min default) |
| **Race conditions** | Lock during verification, only one succeeds |
| **Signature manipulation** | Validate format, recover signer, compare addresses |

### Security Guarantees

1. **Freshness:** Challenge expires after 5 minutes (configurable)
2. **Uniqueness:** Nonce is single-use, tracked in memory
3. **Binding:** Origin + chain ID included in signed message
4. **Atomicity:** Concurrent verification detected and rejected
5. **Integrity:** Signature cryptographically verified via `ecrecover`

### Limitations

1. **In-memory storage** — Challenges lost on restart (use database for production)
2. **No rate limiting** — Add rate limiting for production
3. **No IP binding** — Consider binding to IP for high-value sessions
4. **No hardware wallet support** — `personal_sign` works, but EIP-712 clearer for UI

---

## Test Execution

### Run Full Suite

```bash
cd bounty_008_wallet_signin
./run_tests.sh
```

### Run Individual Components

```bash
# Test suite only
.venv/bin/python test_suite.py

# Demonstrate V1 vulnerability
.venv/bin/python vulnerable_v1_no_nonce.py

# Demonstrate V2 vulnerability
.venv/bin/python vulnerable_v2_no_origin.py
```

---

## Compliance with Acceptance Criteria

✅ **Local test service** — `wallet_signin_service.py`  
✅ **Generated test wallets** — 5 test wallets, no real credentials  
✅ **20+ adversarial cases** — 20 tests across 7 categories  
✅ **Nonce replay** — Tests 2-4  
✅ **Wrong signer** — Tests 5-7  
✅ **Substituted origin** — Tests 8-10  
✅ **Expiration boundary** — Tests 11-14  
✅ **Malformed signature** — Tests 15-18  
✅ **Concurrent verification** — Tests 19-20 (exactly one succeeds)  
✅ **2 vulnerable implementations** — V1 (no nonce), V2 (no origin)  
✅ **Executable runner** — `run_tests.sh`  
✅ **Threat-model notes** — This document  
✅ **No real credentials** — Generated wallets only  
✅ **No production attacks** — Local fixtures only

---

## Files

```
bounty_008_wallet_signin/
├── README.md                      # This document
├── wallet_signin_service.py       # Secure test service
├── test_suite.py                  # 20 adversarial tests
├── vulnerable_v1_no_nonce.py      # Vulnerable: replay attacks
├── vulnerable_v2_no_origin.py     # Vulnerable: CSRF attacks
├── run_tests.sh                   # One-command runner
└── .venv/                         # Virtual environment
```

---

## Dependencies

- Python 3.11+
- `eth_account` (installed in venv)

**Install:**
```bash
python3 -m venv .venv
.venv/bin/pip install eth_account
```

---

## Key Design Decisions

### Why `personal_sign`?

- Widely supported by all Ethereum wallets
- Human-readable message
- Simple to implement

### Why include origin in message?

- Binds signature to specific website
- Prevents CSRF attacks from malicious origins
- User can see where they're signing in

### Why include chain ID?

- Prevents cross-chain replay
- Signature valid only on intended chain
- Important for multi-chain applications

### Why concurrent verification protection?

- Race conditions could allow multiple sessions from single signature
- Lock ensures atomic verification
- Second attempt fails with clear error

---

**Submission Date:** 2026-10-08  
**Test Cases:** 20  
**Pass Rate:** 100.0%  
**Vulnerable Implementations:** 2
