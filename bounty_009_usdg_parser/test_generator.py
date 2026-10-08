#!/usr/bin/env python3
"""
USDG Parser Test Generator - Bounty #9
Generates 100,000+ seeded test cases + 30 hand-selected edge cases.
"""

import random
import json
import hashlib
from decimal import Decimal
from typing import List, Dict, Any
from usdg_parser import (
    parse_usdg_input, format_usdg, USDGParseError,
    parse_and_format, reference_parse, DECIMALS, MAX_VALUE
)

SEED = 20261008  # Fixed seed for reproducibility

def generate_random_valid_cases(n: int, rng: random.Random) -> List[Dict[str, Any]]:
    """Generate random valid test cases."""
    cases = []
    
    for i in range(n):
        case_type = rng.choice([
            'integer', 'decimal', 'small', 'large', 'scientific', 'whitespace'
        ])
        
        try:
            if case_type == 'integer':
                # Random integer
                int_val = rng.randint(0, 1000000)
                input_str = str(int_val)
                expected_raw = int_val * (10**DECIMALS)
            
            elif case_type == 'decimal':
                # Random decimal
                int_part = rng.randint(0, 10000)
                frac_digits = rng.randint(1, DECIMALS)
                frac_part = rng.randint(0, 10**frac_digits - 1)
                input_str = f"{int_part}.{str(frac_part).zfill(frac_digits)}"
                expected_raw = int_part * (10**DECIMALS) + frac_part * (10**(DECIMALS - frac_digits))
            
            elif case_type == 'small':
                # Small values (below 1)
                frac_digits = rng.randint(1, DECIMALS)
                frac_part = rng.randint(1, 10**frac_digits - 1)
                input_str = f"0.{str(frac_part).zfill(frac_digits)}"
                expected_raw = frac_part * (10**(DECIMALS - frac_digits))
            
            elif case_type == 'large':
                # Large values (near max)
                max_raw = MAX_VALUE
                raw = rng.randint(max_raw // 10, max_raw)
                int_part = raw // (10**DECIMALS)
                frac_part = raw % (10**DECIMALS)
                input_str = f"{int_part}.{str(frac_part).zfill(DECIMALS)}"
                expected_raw = raw
            
            elif case_type == 'scientific':
                # Scientific notation
                int_val = rng.randint(1, 1000)
                exp = rng.randint(-5, 5)
                
                # Calculate expected value
                d = Decimal(int_val) * Decimal(10)**exp
                
                # Check if valid for 6 decimals
                d_str = str(d.normalize())
                if '.' in d_str:
                    _, frac = d_str.split('.')
                    if len(frac) <= DECIMALS:
                        input_str = f"{int_val}e{exp}"
                        expected_raw = int(d * Decimal(10**DECIMALS))
                    else:
                        continue
                else:
                    input_str = f"{int_val}e{exp}"
                    expected_raw = int(d * Decimal(10**DECIMALS))
            
            elif case_type == 'whitespace':
                # With whitespace
                int_val = rng.randint(0, 1000)
                ws_left = ' ' * rng.randint(0, 5)
                ws_right = ' ' * rng.randint(0, 5)
                input_str = f"{ws_left}{int_val}{ws_right}"
                expected_raw = int_val * (10**DECIMALS)
            
            else:
                continue
            
            cases.append({
                'input': input_str,
                'expected_raw': expected_raw,
                'category': case_type
            })
        
        except Exception:
            continue
    
    return cases

def generate_random_invalid_cases(n: int, rng: random.Random) -> List[Dict[str, Any]]:
    """Generate random invalid test cases."""
    cases = []
    
    for i in range(n):
        case_type = rng.choice([
            'negative', 'leading_zeros', 'excess_precision', 'hex',
            'multiple_decimals', 'unicode_lookalike', 'empty', 'letters',
            'extreme_exponent', 'signs'
        ])
        
        try:
            if case_type == 'negative':
                input_str = f"-{rng.randint(1, 1000)}"
            
            elif case_type == 'leading_zeros':
                input_str = f"0{rng.randint(10, 999)}"
            
            elif case_type == 'excess_precision':
                int_part = rng.randint(0, 100)
                # Generate 8 fractional digits with non-zero in positions 7-8 (excess)
                frac_valid = rng.randint(1, 10**DECIMALS - 1)  # First 6 digits
                frac_excess = rng.randint(1, 99)  # Last 2 digits (must be non-zero)
                input_str = f"{int_part}.{str(frac_valid).zfill(DECIMALS)}{str(frac_excess).zfill(2)}"
            
            elif case_type == 'hex':
                input_str = f"0x{rng.randint(100, 999):x}"
            
            elif case_type == 'multiple_decimals':
                input_str = f"{rng.randint(1, 100)}.{rng.randint(1, 100)}.{rng.randint(1, 100)}"
            
            elif case_type == 'unicode_lookalike':
                # Use Unicode digits that look like ASCII
                # U+0660 is Arabic-Indic 0
                val = rng.randint(10, 999)
                input_str = ''.join(chr(ord(d) + 0x0660) for d in str(val))
            
            elif case_type == 'empty':
                input_str = rng.choice(['', '   ', '\t', '\n'])
            
            elif case_type == 'letters':
                input_str = ''.join(rng.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(rng.randint(3, 10)))
            
            elif case_type == 'extreme_exponent':
                input_str = f"{rng.randint(1, 100)}e{rng.choice([-200, 200])}"
            
            elif case_type == 'signs':
                input_str = f"{rng.choice(['++', '--', '+-'])}{rng.randint(1, 100)}"
            
            else:
                continue
            
            cases.append({
                'input': input_str,
                'expected': 'REJECT',
                'category': case_type
            })
        
        except Exception:
            continue
    
    return cases

def generate_edge_cases() -> List[Dict[str, Any]]:
    """Generate 30 hand-selected edge cases."""
    return [
        # Boundary cases
        {'input': '0', 'expected_raw': 0, 'category': 'boundary'},
        {'input': '0.0', 'expected_raw': 0, 'category': 'boundary'},
        {'input': '0.000001', 'expected_raw': 1, 'category': 'boundary'},
        {'input': '0.000000', 'expected_raw': 0, 'category': 'boundary'},
        
        # Precision boundaries
        {'input': '0.999999', 'expected_raw': 999999, 'category': 'precision'},
        {'input': '1.000000', 'expected_raw': 1000000, 'category': 'precision'},
        {'input': '1.000001', 'expected_raw': 1000001, 'category': 'precision'},
        
        # Trailing zeros
        {'input': '1.100', 'expected_raw': 1100000, 'category': 'trailing_zeros'},
        {'input': '1.100000', 'expected_raw': 1100000, 'category': 'trailing_zeros'},
        
        # Leading zeros on fraction
        {'input': '0.000001', 'expected_raw': 1, 'category': 'leading_zeros_fraction'},
        {'input': '0.000010', 'expected_raw': 10, 'category': 'leading_zeros_fraction'},
        
        # Scientific notation
        {'input': '1e0', 'expected_raw': 1000000, 'category': 'scientific'},
        {'input': '1e6', 'expected_raw': 1000000000000, 'category': 'scientific'},
        {'input': '1000000e-6', 'expected_raw': 1000000, 'category': 'scientific'},
        
        # Large values
        {'input': '999999999999999999', 'expected_raw': 999999999999999999000000, 'category': 'large'},
        
        # Whitespace
        {'input': '  42  ', 'expected_raw': 42000000, 'category': 'whitespace'},
        {'input': '\t100.5\n', 'expected_raw': 100500000, 'category': 'whitespace'},
        
        # Signs
        {'input': '+1', 'expected_raw': 1000000, 'category': 'sign'},
        {'input': '+0.5', 'expected_raw': 500000, 'category': 'sign'},
        
        # Decimal variations
        {'input': '.5', 'expected_raw': 500000, 'category': 'decimal_var'},
        {'input': '5.', 'expected_raw': 5000000, 'category': 'decimal_var'},
        
        # Zero variations
        {'input': '0', 'expected_raw': 0, 'category': 'zero'},
        {'input': '00', 'expected': 'REJECT', 'category': 'zero_invalid'},
        {'input': '-0', 'expected': 'REJECT', 'category': 'zero_invalid'},
        
        # Unicode rejection
        {'input': '¹²³', 'expected': 'REJECT', 'category': 'unicode'},
        {'input': '⁴⁵⁶', 'expected': 'REJECT', 'category': 'unicode'},
        
        # Multiple operations
        {'input': '1.000001', 'expected_raw': 1000001, 'category': 'exact_precision'},
        
        # Edge precision
        {'input': '123.456789', 'expected_raw': 123456789, 'category': 'full_precision'},
    ]

def run_tests(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run all test cases and collect results."""
    results = {
        'passed': 0,
        'failed': 0,
        'errors': [],
        'details': []
    }
    
    for i, case in enumerate(cases):
        input_str = case['input']
        test_id = f"test_{i:06d}"
        
        try:
            if 'expected_raw' in case:
                # Should parse successfully
                raw = parse_usdg_input(input_str)
                canonical = format_usdg(raw)
                
                if raw == case['expected_raw']:
                    results['passed'] += 1
                    results['details'].append({
                        'id': test_id,
                        'input': input_str,
                        'status': 'PASS',
                        'raw': raw,
                        'canonical': canonical,
                        'category': case.get('category', 'unknown')
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'id': test_id,
                        'input': input_str,
                        'error': f"Expected raw {case['expected_raw']}, got {raw}",
                        'category': case.get('category', 'unknown')
                    })
            
            else:
                # Should reject
                try:
                    raw = parse_usdg_input(input_str)
                    results['failed'] += 1
                    results['errors'].append({
                        'id': test_id,
                        'input': input_str,
                        'error': f"Should reject but got raw={raw}",
                        'category': case.get('category', 'unknown')
                    })
                except USDGParseError as e:
                    results['passed'] += 1
                    results['details'].append({
                        'id': test_id,
                        'input': input_str,
                        'status': 'PASS',
                        'rejected': str(e),
                        'category': case.get('category', 'unknown')
                    })
        
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'id': test_id,
                'input': input_str,
                'error': f"Unexpected exception: {e}",
                'category': case.get('category', 'unknown')
            })
    
    return results

def main():
    print("=== USDG Parser Test Generator ===\n")
    
    # Initialize RNG with fixed seed
    rng = random.Random(SEED)
    
    # Generate test cases
    print("Generating test cases...")
    
    # 100,000 random cases
    valid_cases = generate_random_valid_cases(70000, rng)
    invalid_cases = generate_random_invalid_cases(30000, rng)
    
    # 30 hand-selected edge cases
    edge_cases = generate_edge_cases()
    
    all_cases = valid_cases + invalid_cases + edge_cases
    
    print(f"Generated {len(all_cases)} test cases:")
    print(f"  Valid: {len(valid_cases)}")
    print(f"  Invalid: {len(invalid_cases)}")
    print(f"  Edge: {len(edge_cases)}")
    print()
    
    # Run tests
    print("Running tests...")
    results = run_tests(all_cases)
    
    print(f"\nResults:")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success rate: {results['passed'] / len(all_cases) * 100:.2f}%")
    
    # Save results
    output = {
        'seed': SEED,
        'total_cases': len(all_cases),
        'passed': results['passed'],
        'failed': results['failed'],
        'cases': results['details'],
        'errors': results['errors']
    }
    
    output_file = 'test_results.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    # Generate hash for verification
    content = json.dumps(output, sort_keys=True)
    hash_value = hashlib.sha256(content.encode()).hexdigest()
    print(f"SHA-256 hash: {hash_value}")
    
    # Cross-check with reference implementation
    print("\n=== Cross-check with Decimal reference ===")
    cross_check_errors = 0
    
    for case in valid_cases[:100]:  # Sample 100 cases
        input_str = case['input']
        our_raw = parse_usdg_input(input_str)
        ref_raw = reference_parse(input_str)
        
        if ref_raw is None:
            print(f"  Reference failed for {input_str!r}")
            cross_check_errors += 1
        elif our_raw != ref_raw:
            print(f"  Mismatch for {input_str!r}: our={our_raw}, ref={ref_raw}")
            cross_check_errors += 1
    
    print(f"Cross-check errors: {cross_check_errors}")
    
    # Return exit code
    return 0 if results['failed'] == 0 else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
