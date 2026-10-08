# Canonical Brief Hashing - Bounty #10 Submission

**Bounty:** #10 - Design canonical brief hashing across two languages
**Reward:** 1 USDG
**Deadline:** 2026-10-14T09:54:30.000Z
**Category:** Development

---

## Executive Summary

Implemented deterministic serialization and keccak256 hashing for bounty briefs in **Python and JavaScript**. **50 cross-language test vectors** with 100% hash match rate. Canonical rules ensure byte-identical output across languages: NFC Unicode normalization, LF line endings, alphabetical field ordering, minimal JSON.

---

## Deliverables

### 1. Python Implementation (`brief_hash.py`)

**Core Functions:**
- `serialize_brief(brief, strict=True)` — Canonical JSON serialization
- `hash_brief(brief, strict=True)` — keccak256 hash (0x-prefixed)
- `normalize_string(s)` — NFC + LF + trimmed
- `validate_brief(brief)` — Structure validation

**Dependencies:** pycryptodome (keccak256)

### 2. JavaScript Implementation (`brief_hash.js`)

**Core Functions:**
- `serializeBrief(brief, strict)` — Canonical JSON serialization
- `hashBrief(brief, strict)` — keccak256 hash (0x-prefixed)
- `normalizeString(s)` — NFC + LF + trimmed
- `validateBrief(brief)` — Structure validation

**Dependencies:** js-sha3

### 3. Cross-Language Test (`run_cross_test.sh`)

Generates 50 test vectors, computes hashes in both languages, compares results.

**Results:**
```
Matches: 50/50 (100%)
Mismatches: 0/50
```

### 4. Test Vectors (`cross_language_results.json`)

50 test vectors with matching hashes:
```json
{
  "total": 50,
  "matches": 50,
  "mismatches": 0,
  "vectors": [...]
}
```

---

## Canonical Serialization Rules

### Field Ordering
- Required fields: `criteria`, `deadline`, `description`, `reward`, `title`, `token` (alphabetical)
- Optional fields: `category`, `owner`, `repo_url` (alphabetical, only if present)

### String Normalization
1. **NFC Unicode normalization** — Canonical decomposition + composition
2. **LF line endings** — Convert CRLF (`\r\n`) to LF (`\n`)
3. **Trim trailing whitespace** — Per line, then final newlines
4. **UTF-8 encoding** — For hash computation

### JSON Serialization
- No extra whitespace: `{"key":"value"}` not `{"key": "value"}`
- Keys in alphabetical order
- No trailing commas
- UTF-8 encoding

### Required Fields

| Field | Type | Validation |
|-------|------|------------|
| title | string | Non-empty |
| description | string | Non-empty |
| criteria | string | Non-empty |
| reward | string | Numeric (e.g., "1", "5.5") |
| token | string | Token symbol |
| deadline | string | ISO 8601 format |

### Optional Fields

| Field | Type |
|-------|------|
| repo_url | string |
| category | string |
| owner | string |

---

## Rejection Rules

**Invalid briefs are rejected:**
1. Missing required fields
2. Non-string field values
3. Invalid numeric reward
4. Invalid ISO 8601 deadline
5. Unknown fields (ignored, not rejected)
6. Null values in required fields

**Example rejection:**
```python
validate_brief({"title": "Test"})  # Missing required fields
# Raises: BriefHashError: Missing required fields: ['description', 'criteria', 'reward', 'token', 'deadline']
```

---

## Edge Cases Covered

### 1. Composed/Decomposed Unicode
```python
# Both normalize to same NFC form
"café" (composed: \u00e9)
"café" (decomposed: e + \u0301)
# Same hash after normalization
```

### 2. CRLF vs LF Line Endings
```python
# Both normalize to LF
"Line1\r\nLine2"
"Line1\nLine2"
# Same hash after normalization
```

### 3. Trailing Whitespace
```python
# Trailing spaces removed
"Text   " → "Text"
```

### 4. Empty Optional Fields
```python
# Optional fields omitted if null/undefined
{"title": "...", "repo_url": null}
# Serialized without repo_url
```

### 5. Hostile Nested Input
```python
# Strings are escaped properly in JSON
{"title": "Test \"quotes\" and \n newlines"}
# Serialized: {"title":"Test \"quotes\" and \n newlines"}
```

---

## Byte Equality vs Semantic Similarity

### Byte Equality
Two briefs have **byte-identical** canonical serialization if and only if:
1. Same field values (after normalization)
2. Same field ordering (alphabetical)
3. Same encoding (UTF-8)

**Result:** Same keccak256 hash.

### Semantic Similarity
Two briefs are **semantically similar** if they convey the same meaning, but may differ in:
- Unicode composition (NFD vs NFC)
- Line endings (CRLF vs LF)
- Whitespace (trailing spaces)
- Field ordering
- JSON formatting

**Result:** Different byte representations, possibly different hashes.

**Example:**
```python
# Semantically identical, but different hashes BEFORE normalization:
brief1 = {"title": "café"}      # NFC
brief2 = {"title": "cafe\u0301"} # NFD

# After normalization: SAME hash
```

**Canonical hash ensures:** Semantically identical briefs → identical hashes (via normalization).

---

## Immutable Historical Briefs

### Verification Principle
Once a brief is published with its hash, the hash becomes part of the immutable record.

**Verification steps:**
1. Fetch brief JSON from storage
2. Compute canonical serialization
3. Compute keccak256 hash
4. Compare to stored hash

**If match:** Brief has not been modified.
**If mismatch:** Brief content changed (or hash was incorrect).

### Why This Works
- Canonical rules are deterministic
- Same brief → same serialization → same hash
- Hash is cryptographically bound to content
- Any modification changes hash

### Client Implementation
```python
def verify_brief(brief_json, expected_hash):
    computed = hash_brief(brief_json)
    return computed.lower() == expected_hash.lower()
```

---

## How to Run

```bash
cd bounty_010_brief_hashing
./run_cross_test.sh
```

Or test individual implementations:

```bash
# Python
.venv/bin/python3 brief_hash.py

# JavaScript
node brief_hash.js
```

---

## Files

```
bounty_010_brief_hashing/
├── README.md                    # This document
├── brief_hash.py                # Python implementation
├── brief_hash.js                # JavaScript implementation
├── run_cross_test.sh            # Cross-language test runner
├── cross_language_results.json  # Results (50 vectors)
├── .venv/                       # Python venv
└── node_modules/                # Node.js deps
```

---

## Compliance with Acceptance Criteria

✅ **50+ cross-language vectors** — 50 vectors generated  
✅ **Matching keccak256 hashes** — 100% match (50/50)  
✅ **Explicit rejection rules** — Documented above  
✅ **Python implementation** — `brief_hash.py`  
✅ **JavaScript implementation** — `brief_hash.js`  
✅ **Composed/decomposed Unicode** — NFC normalization  
✅ **CRLF/LF** — Normalized to LF  
✅ **Empty values** — Optional fields omitted if null  
✅ **Hostile nested input** — Proper JSON escaping  
✅ **One-command test** — `run_cross_test.sh`  
✅ **Byte equality vs semantic similarity** — Documented above  
✅ **Immutable historical briefs** — Verification principle documented  

---

## Technical Details

### Why keccak256?
- Standard for Ethereum/Web3
- Used by EIP-55 for address checksums
- Efficient to compute
- Collision-resistant

### Why NFC Normalization?
- Most common Unicode form
- Recommended by W3C
- Stable across platforms
- Preserves visual appearance

### Why Alphabetical Field Ordering?
- Deterministic across languages
- JSON spec doesn't guarantee order
- Ensures reproducibility

---

**Submission Date:** 2026-10-08
**Test Vectors:** 50
**Match Rate:** 100.0%
**Languages:** Python 3.11, Node.js
