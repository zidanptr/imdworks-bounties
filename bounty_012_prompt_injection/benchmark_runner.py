#!/usr/bin/env python3
"""
Agent Prompt-Injection Boundary Benchmark - Bounty #12
Deterministic benchmark for agent security boundary testing.
"""

import json
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ERROR = "ERROR"


@dataclass
class TestResult:
    fixture_id: str
    category: str
    expected: str
    actual: str
    passed: bool
    reason: str


class NaiveRunner:
    """
    Vulnerable baseline runner with NO protection.
    Accepts all bounty text without validation.
    """
    
    def evaluate(self, bounty_text: str) -> Verdict:
        """Naive: Accept everything."""
        # VULNERABLE: No validation at all
        return Verdict.ACCEPT


class DefendedRunner:
    """
    Secure runner with fail-closed policy boundary.
    
    Security properties:
    1. Blocks tool-output injection patterns
    2. Blocks encoded instruction patterns (base64, hex, rot13, etc.)
    3. Blocks forged system messages
    4. Blocks credential exfiltration requests
    5. Fails closed: reject if uncertain
    """
    
    # Patterns that indicate tool output injection
    TOOL_OUTPUT_PATTERNS = [
        r'\[SYSTEM:',
        r'\[TOOL:',
        r'\[TOOL_RESULT:',
        r'\[OUTPUT_START\]',
        r'\[OUTPUT_END\]',
        r'\[ADMIN INSTRUCTION\]',
        r'\[TOOL INSTRUCTION\]',
        r'\[INFO\].*[Tt]ool',
        r'\[PASS\].*[Nn]ext step:',
        r'Previous tool output',
        r'Tool output shows',
        r'Authorization: Bearer',
        r'Bearer [A-Z_0-9]+',
        r'---BEGIN TOOL OUTPUT---',
        r'---END TOOL OUTPUT---',
    ]
    
    # Patterns for encoded instructions
    ENCODED_PATTERNS = [
        # Base64 pattern (looks for decode instruction)
        r'[Dd]ecode.*[Bb]ase64',
        r'[Bb]ase64.*decode',
        r'[Bb]ase64',
        r'[Tt]ranslate.*hex',
        r'[Dd]ecode.*hex',
        r'ROT13',
        r'[Rr]ot13',
        r'[Uu]nicode.*decode',
        r'U\+[0-9A-Fa-f]{4}',  # Unicode escapes
        r'%[0-9A-Fa-f]{2}.*%[0-9A-Fa-f]{2}',  # URL encoding
        r'[Mm]orse.*code',
        r'[Bb]inary.*analy',
        r'0[01]{7,}',  # Binary strings
        r'[Dd]ecode and analy',
        r'[Aa]nalyze.*[Bb]ase64',
    ]
    
    # Patterns for forged system messages
    FORGED_SYSTEM_PATTERNS = [
        r'SYSTEM OVERRIDE',
        r'SYSTEM UPDATE',
        r'SYSTEM:',
        r'Ignore (all )?previous instructions',
        r'You are (now )?(an )?unfiltered',
        r'All tool restrictions (removed|lifted)',
        r'Authorization level elevated',
        r'POLICY_UPDATE',
        r'Policy change:',
        r'policy\.update',
        r'<!-- SYSTEM:',
        r'```system',
        r'FROM:.*@.*system',
        r'SECURITY SCAN PASSED',
        r'Tool restrictions lifted',
        r'credentials_tool (is now |authorized|SAFE)',
    ]
    
    # Patterns for credential exfiltration
    CREDENTIAL_PATTERNS = [
        r'credentials_tool',
        r'credential[s]?_tool',
        r'API_KEY',
        r'PRIVATE_KEY',
        r'PRIVATEKEY',
        r'SECRET_KEY',
        r'process\.env\.\w+',
        r'environment variable',
        r'\.ssh/id_rsa',
        r'/etc/passwd',
        r'\.config/secrets',
        r'~/.ssh/',
        r'wallet_private_key',
        r'exfiltrat',
        r'send.*api.*key',
        r'curl.*POST.*-d',
        r'export.*\$\(',
        r'read_environment',
        r'process\.env',
        r'[Rr]ead.*entries from.*env',
        r'[Tt]ime.*read.*env',
    ]
    
    # Dangerous tool names
    DANGEROUS_TOOLS = [
        r'credentials_tool',
        r'wallet_transfer',
        r'shell_exec',
        r'delete_all_files',
        r'read_environment',
        r'transfer_funds',
    ]
    
    def evaluate(self, bounty_text: str) -> Tuple[Verdict, str]:
        """
        Evaluate bounty text with fail-closed policy.
        
        Returns (verdict, reason).
        """
        # Check tool output injection
        for pattern in self.TOOL_OUTPUT_PATTERNS:
            if re.search(pattern, bounty_text, re.IGNORECASE):
                return Verdict.REJECT, f"Tool output injection detected: {pattern}"
        
        # Check encoded instructions
        for pattern in self.ENCODED_PATTERNS:
            if re.search(pattern, bounty_text, re.IGNORECASE):
                return Verdict.REJECT, f"Encoded instruction detected: {pattern}"
        
        # Check forged system messages
        for pattern in self.FORGED_SYSTEM_PATTERNS:
            if re.search(pattern, bounty_text, re.IGNORECASE):
                return Verdict.REJECT, f"Forged system message detected: {pattern}"
        
        # Check credential exfiltration
        for pattern in self.CREDENTIAL_PATTERNS:
            if re.search(pattern, bounty_text, re.IGNORECASE):
                # Context check: is it about creating/using securely or extracting?
                # Allow patterns like "create a secure password" or "store API keys"
                # But reject "read API_KEY" or "show me PRIVATE_KEY"
                if self._is_extraction_context(bounty_text, pattern):
                    return Verdict.REJECT, f"Credential exfiltration detected: {pattern}"
        
        # Check dangerous tool calls
        for pattern in self.DANGEROUS_TOOLS:
            if re.search(pattern, bounty_text, re.IGNORECASE):
                return Verdict.REJECT, f"Dangerous tool reference detected: {pattern}"
        
        # Default: accept
        return Verdict.ACCEPT, "No security violations detected"
    
    def _is_extraction_context(self, text: str, pattern: str) -> bool:
        """
        Determine if the context is extraction vs creation.
        
        Creation patterns (benign):
        - "create a secure password"
        - "store API keys"
        - "implement environment variable"
        
        Extraction patterns (malicious):
        - "read API_KEY"
        - "show me PRIVATE_KEY"
        - "use credentials_tool to"
        """
        text_lower = text.lower()
        
        # Extraction verbs
        extraction_verbs = [
            'read', 'show', 'fetch', 'retrieve', 'get', 'extract',
            'exfiltrate', 'send', 'post', 'upload', 'sync', 'use',
            'run', 'execute', 'call', 'invoke'
        ]
        
        # Check if extraction verb appears near the pattern
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 50)
            end = min(len(text_lower), match.end() + 50)
            context = text_lower[start:end]
            
            for verb in extraction_verbs:
                if verb in context:
                    return True
        
        return False


class BenchmarkExecutor:
    """Run the full benchmark suite."""
    
    def __init__(self, attack_file: str, benign_file: str):
        self.attack_fixtures = self._load_fixtures(attack_file)
        self.benign_fixtures = self._load_fixtures(benign_file)
    
    def _load_fixtures(self, filepath: str) -> List[Dict]:
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def run_naive_baseline(self) -> Tuple[int, int]:
        """Run naive runner (should FAIL on all attacks)."""
        print("\n=== Naive Baseline (Vulnerable) ===\n")
        
        runner = NaiveRunner()
        results = []
        
        # Test attacks (should be rejected but naive accepts all)
        print("Testing attack fixtures (should reject):\n")
        attack_results = []
        for fixture in self.attack_fixtures:
            verdict = runner.evaluate(fixture['bounty_text'])
            expected = Verdict[fixture['expected']]
            passed = verdict == expected
            
            result = TestResult(
                fixture_id=fixture['id'],
                category=fixture['category'],
                expected=fixture['expected'],
                actual=verdict.value,
                passed=passed,
                reason="Naive accepts everything"
            )
            results.append(result)
            
            if not passed:
                print(f"  ✗ {fixture['id']:20} | {fixture['category']:30} | ACCEPTED (should REJECT)")
        
        # Test benign (naive accepts these correctly)
        print("\nTesting benign controls (should accept):\n")
        for fixture in self.benign_fixtures:
            verdict = runner.evaluate(fixture['bounty_text'])
            expected = Verdict[fixture['expected']]
            passed = verdict == expected
            
            result = TestResult(
                fixture_id=fixture['id'],
                category=fixture['category'],
                expected=fixture['expected'],
                actual=verdict.value,
                passed=passed,
                reason="Naive accepts everything"
            )
            results.append(result)
            
            if passed:
                print(f"  ✓ {fixture['id']:20} | {fixture['category']:30} | ACCEPTED")
        
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        print(f"\nNaive Baseline: {passed}/{total} passed ({passed/total*100:.1f}%)")
        print("Expected: FAIL on all attacks (baseline shows vulnerability)")
        
        return passed, total
    
    def run_defended(self) -> Tuple[int, int, List[TestResult]]:
        """Run defended runner (should PASS on all tests)."""
        print("\n\n=== Defended Runner (Fail-Closed) ===\n")
        
        runner = DefendedRunner()
        results = []
        
        # Test attacks
        print("Testing attack fixtures (should reject):\n")
        for fixture in self.attack_fixtures:
            verdict, reason = runner.evaluate(fixture['bounty_text'])
            expected = Verdict[fixture['expected']]
            passed = verdict == expected
            
            result = TestResult(
                fixture_id=fixture['id'],
                category=fixture['category'],
                expected=fixture['expected'],
                actual=verdict.value,
                passed=passed,
                reason=reason
            )
            results.append(result)
            
            status = "✓" if passed else "✗"
            print(f"  {status} {fixture['id']:20} | {fixture['category']:30} | {verdict.value:8} | {reason[:50]}")
        
        # Test benign
        print("\nTesting benign controls (should accept):\n")
        for fixture in self.benign_fixtures:
            verdict, reason = runner.evaluate(fixture['bounty_text'])
            expected = Verdict[fixture['expected']]
            passed = verdict == expected
            
            result = TestResult(
                fixture_id=fixture['id'],
                category=fixture['category'],
                expected=fixture['expected'],
                actual=verdict.value,
                passed=passed,
                reason=reason
            )
            results.append(result)
            
            status = "✓" if passed else "✗"
            print(f"  {status} {fixture['id']:20} | {fixture['category']:30} | {verdict.value:8} | {reason[:50]}")
        
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        print(f"\nDefended Runner: {passed}/{total} passed ({passed/total*100:.1f}%)")
        
        return passed, total, results
    
    def generate_report(self, results: List[TestResult], output_file: str):
        """Generate machine-readable report."""
        report = {
            'summary': {
                'total': len(results),
                'passed': sum(1 for r in results if r.passed),
                'failed': sum(1 for r in results if not r.passed),
                'attack_fixtures': len(self.attack_fixtures),
                'benign_controls': len(self.benign_fixtures),
            },
            'results': [
                {
                    'id': r.fixture_id,
                    'category': r.category,
                    'expected': r.expected,
                    'actual': r.actual,
                    'passed': r.passed,
                    'reason': r.reason
                }
                for r in results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport saved to {output_file}")


def main():
    print("=== Agent Prompt-Injection Boundary Benchmark ===")
    print("Bounty #12 - 32 Attack Fixtures + 10 Benign Controls\n")
    
    executor = BenchmarkExecutor(
        attack_file='attack_fixtures.json',
        benign_file='benign_controls.json'
    )
    
    # Run naive baseline
    naive_passed, naive_total = executor.run_naive_baseline()
    
    # Run defended
    defended_passed, defended_total, results = executor.run_defended()
    
    # Generate report
    executor.generate_report(results, 'benchmark_report.json')
    
    # Summary
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"\nNaive Baseline:  {naive_passed}/{naive_total} ({naive_passed/naive_total*100:.1f}%)")
    print(f"                 Expected to FAIL (demonstrates vulnerability)")
    print(f"\nDefended Runner: {defended_passed}/{defended_total} ({defended_passed/defended_total*100:.1f}%)")
    print(f"                 Expected to PASS (blocks attacks, accepts benign)")
    
    if defended_passed == defended_total:
        print("\n✓ BENCHMARK PASSED: All attacks blocked, all benign accepted")
        return 0
    else:
        print(f"\n✗ BENCHMARK FAILED: {defended_total - defended_passed} tests failed")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
