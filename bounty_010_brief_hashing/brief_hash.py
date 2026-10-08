#!/usr/bin/env python3
"""
Canonical Brief Hashing - Python Implementation - Bounty #10
Deterministic serialization and keccak256 hashing for bounty briefs.
"""

import json
from typing import Dict, Optional, Any
from hashlib import sha3_256

try:
    from Crypto.Hash import keccak
    HAS_KECCAK = True
except ImportError:
    HAS_KECCAK = False
    print("Warning: pycryptodome not installed. Install with: pip install pycryptodome")


class BriefHashError(Exception):
    """Raised when brief cannot be hashed."""
    pass


REQUIRED_FIELDS = ['title', 'description', 'criteria', 'reward', 'token', 'deadline']
OPTIONAL_FIELDS = ['repo_url', 'category', 'owner']


def normalize_string(s: str) -> str:
    """
    Normalize string for canonical representation.
    
    Rules:
    - UTF-8 encoding
    - NFC normalization (canonical decomposition + composition)
    - No trailing whitespace
    - LF line endings (convert CRLF to LF)
    """
    import unicodedata
    
    if not isinstance(s, str):
        raise BriefHashError(f"Expected string, got {type(s).__name__}")
    
    # NFC normalization
    s = unicodedata.normalize('NFC', s)
    
    # Convert CRLF to LF
    s = s.replace('\r\n', '\n')
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in s.split('\n')]
    s = '\n'.join(lines)
    
    # Remove trailing newlines
    s = s.rstrip('\n')
    
    return s


def validate_brief(brief: Dict[str, Any]) -> None:
    """
    Validate brief structure.
    
    Required fields: title, description, criteria, reward, token, deadline
    Raises BriefHashError if invalid.
    """
    if not isinstance(brief, dict):
        raise BriefHashError(f"Expected dict, got {type(brief).__name__}")
    
    # Check required fields
    missing = [f for f in REQUIRED_FIELDS if f not in brief]
    if missing:
        raise BriefHashError(f"Missing required fields: {missing}")
    
    # Validate types
    for field in REQUIRED_FIELDS:
        if not isinstance(brief[field], str):
            raise BriefHashError(f"Field '{field}' must be string, got {type(brief[field]).__name__}")
    
    # Validate reward is numeric string
    try:
        float(brief['reward'])
    except ValueError:
        raise BriefHashError(f"Field 'reward' must be numeric string, got: {brief['reward']}")
    
    # Validate deadline is ISO 8601
    import re
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    if not re.match(iso_pattern, brief['deadline']):
        raise BriefHashError(f"Field 'deadline' must be ISO 8601 format, got: {brief['deadline']}")


def serialize_brief(brief: Dict[str, Any], strict: bool = True) -> str:
    """
    Serialize brief to canonical JSON string.
    
    Canonical rules:
    1. Only include required + present optional fields
    2. Fields in alphabetical order
    3. No extra whitespace
    4. UTF-8 encoding
    5. Strings normalized (NFC, LF line endings)
    
    Args:
        brief: Brief dictionary
        strict: If True, validate structure before serialization
    
    Returns:
        Canonical JSON string
    """
    if strict:
        validate_brief(brief)
    
    # Build canonical dict with only allowed fields
    canonical = {}
    
    # Add all required fields (normalized)
    for field in sorted(REQUIRED_FIELDS):
        canonical[field] = normalize_string(brief[field])
    
    # Add optional fields if present
    for field in sorted(OPTIONAL_FIELDS):
        if field in brief and brief[field] is not None:
            canonical[field] = normalize_string(brief[field])
    
    # Serialize to JSON with no extra whitespace
    return json.dumps(canonical, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def hash_brief(brief: Dict[str, Any], strict: bool = True) -> str:
    """
    Compute keccak256 hash of canonical brief serialization.
    
    Args:
        brief: Brief dictionary
        strict: If True, validate structure before hashing
    
    Returns:
        Hex string of keccak256 hash (0x-prefixed)
    """
    if not HAS_KECCAK:
        raise BriefHashError("pycryptodome required. Install with: pip install pycryptodome")
    
    canonical = serialize_brief(brief, strict=strict)
    
    # Encode to UTF-8 bytes
    data = canonical.encode('utf-8')
    
    # Compute keccak256
    k = keccak.new(digest_bits=256)
    k.update(data)
    hash_bytes = k.digest()
    
    return '0x' + hash_bytes.hex()


def hash_brief_sha256(brief: Dict[str, Any], strict: bool = True) -> str:
    """
    Compute SHA-256 hash of canonical brief serialization.
    
    Useful for environments without keccak256.
    """
    canonical = serialize_brief(brief, strict=strict)
    data = canonical.encode('utf-8')
    hash_bytes = sha3_256(data).digest()
    return '0x' + hash_bytes.hex()


# Test vectors for cross-language verification
TEST_VECTORS = [
    {
        "brief": {
            "title": "Test Bounty",
            "description": "Simple test case",
            "criteria": "Pass all tests",
            "reward": "1",
            "token": "USDG",
            "deadline": "2026-10-14T09:54:30.000Z"
        },
        "expected_fields": ["criteria", "deadline", "description", "reward", "title", "token"]
    },
    {
        "brief": {
            "title": "Unicode Test \u00e9\u00e8\u00ea",
            "description": "Testing NFC normalization: caf\u00e9",
            "criteria": "Handle Unicode correctly",
            "reward": "5.5",
            "token": "ETH",
            "deadline": "2026-10-15T00:00:00.000Z"
        },
        "expected_fields": ["criteria", "deadline", "description", "reward", "title", "token"]
    },
    {
        "brief": {
            "title": "With Optional Fields",
            "description": "Brief with repo_url",
            "criteria": "Complete implementation",
            "reward": "10",
            "token": "USDG",
            "deadline": "2026-10-20T12:00:00.000Z",
            "repo_url": "https://github.com/example/repo",
            "category": "Development"
        },
        "expected_fields": ["category", "criteria", "deadline", "description", "repo_url", "reward", "title", "token"]
    },
    {
        "brief": {
            "title": "Line Ending Test",
            "description": "Line1\r\nLine2\r\nLine3",
            "criteria": "Normalize CRLF to LF",
            "reward": "1",
            "token": "USDG",
            "deadline": "2026-10-14T00:00:00.000Z"
        },
        "expected_fields": ["criteria", "deadline", "description", "reward", "title", "token"]
    },
    {
        "brief": {
            "title": "Trailing Whitespace",
            "description": "Text with trailing spaces   ",
            "criteria": "Remove trailing whitespace  ",
            "reward": "2",
            "token": "USDG",
            "deadline": "2026-10-14T00:00:00.000Z"
        },
        "expected_fields": ["criteria", "deadline", "description", "reward", "title", "token"]
    }
]


def generate_test_vectors(n: int = 50) -> list:
    """Generate additional test vectors."""
    import random
    import string
    
    vectors = TEST_VECTORS.copy()
    
    # Seed for reproducibility
    random.seed(20261008)
    
    for i in range(n - len(vectors)):
        # Generate random brief
        title = ''.join(random.choices(string.ascii_letters + ' ', k=random.randint(10, 50)))
        desc = ' '.join([''.join(random.choices(string.ascii_letters, k=random.randint(5, 15))) 
                         for _ in range(random.randint(10, 30))])
        criteria = ' '.join([''.join(random.choices(string.ascii_letters, k=random.randint(5, 10))) 
                            for _ in range(random.randint(5, 15))])
        reward = str(random.uniform(0.1, 100.0))
        
        brief = {
            "title": title.strip(),
            "description": desc,
            "criteria": criteria,
            "reward": reward,
            "token": random.choice(["USDG", "ETH", "IMDBTY"]),
            "deadline": f"2026-10-{random.randint(15, 28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}.000Z"
        }
        
        if random.random() > 0.5:
            brief["category"] = random.choice(["Development", "Security", "Data", "Research", "Smart contracts"])
        
        vectors.append({"brief": brief, "expected_fields": sorted(brief.keys())})
    
    return vectors


if __name__ == '__main__':
    import sys
    
    print("=== Canonical Brief Hashing - Python ===\n")
    
    if not HAS_KECCAK:
        print("ERROR: pycryptodome required for keccak256")
        print("Install: pip install pycryptodome\n")
        sys.exit(1)
    
    # Test basic hashing
    print("Test Vectors:\n")
    for i, tv in enumerate(TEST_VECTORS, 1):
        brief = tv['brief']
        canonical = serialize_brief(brief)
        hash_val = hash_brief(brief)
        
        print(f"Vector {i}:")
        print(f"  Title: {brief['title'][:30]}...")
        print(f"  Canonical: {canonical[:80]}...")
        print(f"  Hash: {hash_val}")
        print()
    
    # Generate 50 vectors
    print("\nGenerating 50 test vectors...")
    vectors = generate_test_vectors(50)
    print(f"Generated {len(vectors)} vectors\n")
    
    # Hash all
    print("Hashing all vectors...")
    for i, v in enumerate(vectors, 1):
        h = hash_brief(v['brief'])
        if i % 10 == 0:
            print(f"  {i}/{len(vectors)}: {h[:20]}...{h[-20:]}")
    
    print(f"\nAll {len(vectors)} vectors hashed successfully")
