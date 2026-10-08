#!/usr/bin/env python3
"""
USDG Decimal Parser - Bounty #9
Six-decimal token amount parser/formatter using integer arithmetic.
"""

import re
import math
from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional, Union

DECIMALS = 6
MAX_VALUE = (2**256 - 1) // (10**DECIMALS)  # Max raw token amount

class USDGParseError(Exception):
    """Raised when input cannot be parsed unambiguously."""
    pass

def normalize_unicode_digits(s: str) -> str:
    """Convert Unicode digit lookalikes to ASCII."""
    # Common Unicode digit ranges
    result = []
    for ch in s:
        code = ord(ch)
        # Arabic-Indic digits (U+0660-U+0669)
        if 0x0660 <= code <= 0x0669:
            result.append(chr(code - 0x0660 + ord('0')))
        # Extended Arabic-Indic digits (U+06F0-U+06F9)
        elif 0x06F0 <= code <= 0x06F9:
            result.append(chr(code - 0x06F0 + ord('0')))
        # Superscript digits (for rejection)
        elif ch in '⁰¹²³⁴⁵⁶⁷⁸⁹':
            raise USDGParseError(f"Unicode superscript digit '{ch}' not accepted")
        # Fullwidth digits (U+FF10-U+FF19)
        elif 0xFF10 <= code <= 0xFF19:
            result.append(chr(code - 0xFF10 + ord('0')))
        else:
            result.append(ch)
    return ''.join(result)

def parse_usdg_input(s: str) -> int:
    """
    Parse user input to raw token amount (integer, 6 decimals implied).
    
    Grammar:
        input      ::= [whitespace] [sign] integer [fraction] [exponent] [whitespace]
        integer    ::= '0' | nonzero_digit digit*
        fraction   ::= '.' digit*
        exponent   ::= ('e' | 'E') [sign] digit+
        sign       ::= '+' | '-'
        digit      ::= '0'..'9'
        whitespace ::= any Unicode whitespace
    
    Returns raw amount (e.g., "1.5" -> 1500000)
    Raises USDGParseError for ambiguous/lossy inputs.
    """
    if not isinstance(s, str):
        raise USDGParseError(f"Expected string, got {type(s).__name__}")
    
    # Strip whitespace
    s = s.strip()
    if not s:
        raise USDGParseError("Empty input")
    
    # Normalize Unicode digits (may raise for lookalikes)
    s = normalize_unicode_digits(s)
    
    # Reject multiple signs, embedded signs
    if s.count('+') > 1 or s.count('-') > 1:
        raise USDGParseError("Multiple signs not allowed")
    
    # Check for sign
    negative = False
    if s.startswith('-'):
        negative = True
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]
    
    # Reject hexadecimal, octal, binary prefixes
    if s.lower().startswith(('0x', '0o', '0b')):
        raise USDGParseError("Number prefixes not accepted")
    
    # Parse exponent
    exponent = 0
    if 'e' in s or 'E' in s:
        match = re.match(r'^(.+?)[eE]([+-]?\d+)$', s)
        if not match:
            raise USDGParseError("Malformed exponent")
        mantissa, exp_str = match.groups()
        s = mantissa
        try:
            exponent = int(exp_str)
        except ValueError:
            raise USDGParseError(f"Invalid exponent: {exp_str}")
        
        # Reject extreme exponents
        if abs(exponent) > 100:
            raise USDGParseError(f"Exponent {exponent} out of range")
    
    # Validate mantissa format
    if not re.match(r'^\d+\.?\d*$|^\d*\.?\d+$', s):
        raise USDGParseError(f"Invalid number format: {s}")
    
    # Reject leading zeros on multi-digit integers (ambiguous)
    if '.' not in s:
        if len(s) > 1 and s[0] == '0':
            raise USDGParseError("Leading zeros on integer not accepted")
    else:
        int_part, frac_part = s.split('.', 1)
        # Reject leading zeros on integer part (except "0.xxx")
        if len(int_part) > 1 and int_part[0] == '0':
            raise USDGParseError("Leading zeros on integer part not accepted")
        # Reject trailing zeros after decimal if we'd lose precision
        # (We accept them but check precision later)
    
    # Split into integer and fractional parts
    if '.' in s:
        int_part, frac_part = s.split('.', 1)
    else:
        int_part, frac_part = s, ''
    
    # Handle empty parts
    if not int_part and not frac_part:
        raise USDGParseError("No digits")
    
    int_part = int_part or '0'
    
    # Check for excess precision
    if len(frac_part) > DECIMALS:
        # Check if excess digits are all zeros (acceptable)
        excess = frac_part[DECIMALS:]
        if excess.strip('0'):
            raise USDGParseError(f"Excess precision: {len(frac_part)} fractional digits > {DECIMALS}")
        # Trim trailing zeros
        frac_part = frac_part[:DECIMALS]
    
    # Apply exponent adjustment
    if exponent != 0:
        # Combine integer and fractional parts
        total_digits = int_part + frac_part
        
        if exponent > 0:
            # Move decimal right: add zeros to the right
            total_digits = total_digits + '0' * exponent
            # All digits become integer part
            int_part = total_digits
            frac_part = ''
        else:  # exponent < 0
            # Move decimal left
            shift = -exponent
            if len(total_digits) <= shift:
                # Result is fractional
                int_part = '0'
                frac_part = '0' * (shift - len(total_digits)) + total_digits
            else:
                int_part = total_digits[:-shift]
                frac_part = total_digits[-shift:]
        
        # Check precision after exponent adjustment
        if len(frac_part) > DECIMALS:
            excess = frac_part[DECIMALS:]
            if excess.strip('0'):
                raise USDGParseError(f"Exponent creates excess precision")
            frac_part = frac_part[:DECIMALS]
    
    # Combine and convert to integer
    frac_part = (frac_part + '0' * DECIMALS)[:DECIMALS]
    raw_str = int_part + frac_part
    
    try:
        raw = int(raw_str)
    except ValueError:
        raise USDGParseError(f"Cannot convert to integer: {raw_str}")
    
    # Check range
    if raw > MAX_VALUE:
        raise USDGParseError(f"Value exceeds maximum: {raw}")
    
    if negative:
        raise USDGParseError("Negative amounts not accepted")
    
    return raw

def format_usdg(raw: int, trim_zeros: bool = True) -> str:
    """
    Format raw token amount to canonical display representation.
    
    Canonical format:
        - No leading zeros on integer part
        - No trailing zeros on fractional part (unless trim_zeros=False)
        - Exactly 6 decimal places if trim_zeros=False
        - No sign (only positive amounts)
    
    Args:
        raw: Raw token amount (integer, 6 decimals implied)
        trim_zeros: If True, remove trailing zeros from fraction
    
    Returns canonical string representation.
    """
    if not isinstance(raw, int):
        raise ValueError(f"Expected integer, got {type(raw).__name__}")
    if raw < 0:
        raise ValueError("Negative amounts not supported")
    if raw > MAX_VALUE:
        raise ValueError(f"Value exceeds maximum: {raw}")
    
    # Convert to string with 6 decimal places
    int_part = raw // (10**DECIMALS)
    frac_part = raw % (10**DECIMALS)
    
    if frac_part == 0:
        return str(int_part)
    
    frac_str = str(frac_part).zfill(DECIMALS)
    
    if trim_zeros:
        frac_str = frac_str.rstrip('0')
    
    return f"{int_part}.{frac_str}"

def format_usdg_fixed(raw: int) -> str:
    """Format with exactly 6 decimal places."""
    int_part = raw // (10**DECIMALS)
    frac_part = raw % (10**DECIMALS)
    frac_str = str(frac_part).zfill(DECIMALS)
    return f"{int_part}.{frac_str}"

def parse_and_format(s: str) -> str:
    """Parse input and return canonical format."""
    raw = parse_usdg_input(s)
    return format_usdg(raw)

def round_trip(s: str) -> Tuple[int, str, str]:
    """
    Parse input and format back.
    Returns (raw_amount, canonical_format, input_normalized).
    """
    raw = parse_usdg_input(s)
    canonical = format_usdg(raw)
    return raw, canonical, s.strip()

# Reference implementation using Decimal for cross-check
def reference_parse(s: str) -> Optional[int]:
    """
    Reference implementation using Python Decimal.
    Returns None if parsing fails or precision is lost.
    """
    try:
        # Try our parser first
        raw = parse_usdg_input(s)
        
        # Cross-check with Decimal
        d = Decimal(s)
        
        # Check if negative
        if d < 0:
            return None
        
        # Check precision
        d_str = str(d.normalize())
        if '.' in d_str:
            _, frac = d_str.split('.')
            if len(frac) > DECIMALS:
                # Check if we lose precision
                if Decimal(raw) / Decimal(10**DECIMALS) != d:
                    return None
        
        return raw
    except (USDGParseError, InvalidOperation, ValueError):
        return None

def demonstrate_floating_point_errors():
    """
    Demonstrate floating-point counterexamples showing why
    float should not be used for token amounts.
    """
    counterexamples = []
    
    # Example 1: 0.1 + 0.2 != 0.3
    a = 0.1
    b = 0.2
    expected = 0.3
    actual = a + b
    if actual != expected:
        counterexamples.append({
            'case': '0.1 + 0.2 != 0.3',
            'float_result': actual,
            'expected': expected,
            'difference': actual - expected,
            'raw_correct': parse_usdg_input('0.3'),
            'float_wrong': int(actual * 10**DECIMALS)
        })
    
    # Example 2: Precision loss on large numbers
    large = 1e20
    added = large + 1
    if added == large:
        counterexamples.append({
            'case': '1e20 + 1 == 1e20',
            'float_result': added,
            'expected': '1e20 + 1',
            'difference': 0,
            'note': 'Integer addition lost due to float precision'
        })
    
    # Example 3: Decimal representation error
    val = 0.1
    raw_from_float = int(val * 10**DECIMALS)
    raw_correct = parse_usdg_input('0.1')
    if raw_from_float != raw_correct:
        counterexamples.append({
            'case': '0.1 * 10^6 != 100000',
            'float_result': raw_from_float,
            'expected': raw_correct,
            'difference': raw_from_float - raw_correct,
            'float_value': val,
            'float_repr': repr(val)
        })
    
    return counterexamples

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Parse command-line input
        for arg in sys.argv[1:]:
            try:
                raw = parse_usdg_input(arg)
                canonical = format_usdg(raw)
                print(f"Input: {arg!r} -> Raw: {raw} -> Canonical: {canonical}")
            except USDGParseError as e:
                print(f"Input: {arg!r} -> REJECTED: {e}")
    else:
        # Run self-test
        print("=== USDG Parser Self-Test ===\n")
        
        # Basic cases
        test_cases = [
            '1',
            '1.0',
            '1.5',
            '0.5',
            '0.000001',
            '1000000',
            '123.456789',
            '  42.5  ',  # Whitespace
            '+5',
            '1e6',
            '1.5e2',
            '150e-2',
        ]
        
        print("Accepted cases:")
        for tc in test_cases:
            try:
                raw = parse_usdg_input(tc)
                canonical = format_usdg(raw)
                print(f"  {tc!r:20} -> raw={raw:15d} -> {canonical}")
            except USDGParseError as e:
                print(f"  {tc!r:20} -> REJECTED: {e}")
        
        print("\nRejected cases:")
        reject_cases = [
            '-1',           # Negative
            '007',          # Leading zeros
            '1.1234567',    # Excess precision
            'abc',          # Non-numeric
            '',             # Empty
            '1.2.3',        # Multiple decimals
            '0x10',         # Hex prefix
        ]
        
        for tc in reject_cases:
            try:
                raw = parse_usdg_input(tc)
                print(f"  {tc!r:20} -> ACCEPTED (unexpected!) -> {raw}")
            except USDGParseError as e:
                print(f"  {tc!r:20} -> REJECTED: {e}")
        
        print("\n=== Floating-Point Counterexamples ===")
        for ex in demonstrate_floating_point_errors():
            print(f"\nCase: {ex['case']}")
            for k, v in ex.items():
                if k != 'case':
                    print(f"  {k}: {v}")
