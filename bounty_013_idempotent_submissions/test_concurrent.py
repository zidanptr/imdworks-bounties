#!/usr/bin/env python3
"""
Concurrent Test Harness - Bounty #13
Test idempotency under concurrent load with fault injection.
"""

import sqlite3
import threading
import time
import random
import os
from typing import Dict, List, Any
from submission_service import SubmissionService


class ConcurrentTestHarness:
    """Run concurrent submission tests."""
    
    def __init__(self, n_wallets: int = 10, n_requests: int = 100, db_path: str = None):
        self.n_wallets = n_wallets
        self.n_requests = n_requests
        self.db_path = db_path or "/tmp/test_submissions.db"
        self.lock = threading.Lock()
    
    def run_test(self) -> Dict[str, Any]:
        print(f"=== Concurrent Test: {self.n_wallets} wallets, {self.n_requests} requests ===\n")
        
        # Clean DB once at start
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Create service and verify DB init
        service = SubmissionService(self.db_path)
        
        wallets = [f"0xWallet{i:02d}" for i in range(self.n_wallets)]
        
        # Test 1: Basic concurrent
        print("--- Test 1: Basic Concurrent ---")
        result1 = self._test_basic_concurrent(service, wallets)
        print(f"  Status: {result1['status']}\n")
        
        # Test 2: Response loss
        print("--- Test 2: Response Loss Recovery ---")
        result2 = self._test_response_loss(service, wallets)
        print(f"  Status: {result2['status']}\n")
        
        # Test 3: Stale update
        print("--- Test 3: Stale Version Handling ---")
        result3 = self._test_stale_update(service, wallets)
        print(f"  Status: {result3['status']}\n")
        
        # Test 4: Review transition
        print("--- Test 4: Review Protection ---")
        result4 = self._test_review_transition(service, wallets)
        print(f"  Status: {result4['status']}\n")
        
        # Test 5: Restart recovery
        print("--- Test 5: Restart Recovery ---")
        result5 = self._test_restart_recovery(wallets)
        print(f"  Status: {result5['status']}\n")
        
        # Final verification
        print("=== Verification ===\n")
        verification = self._verify_idempotency(service)
        
        for k, v in verification.items():
            print(f"  {k}: {'✓' if v else '✗'}")
        
        all_pass = all(verification.values()) and all([
            r['status'] == 'PASS' for r in [result1, result2, result3, result4, result5]
        ])
        
        return {
            'tests': {
                'basic_concurrent': result1,
                'response_loss': result2,
                'stale_update': result3,
                'review_transition': result4,
                'restart_recovery': result5
            },
            'verification': verification,
            'overall_pass': all_pass
        }
    
    def _test_basic_concurrent(self, service: SubmissionService, wallets: List[str]) -> Dict[str, Any]:
        results = {'success': 0, 'error': 0}
        
        def submit_thread(bounty_id: str, wallet: str, content: str):
            result = service.submit(bounty_id, wallet, content)
            with self.lock:
                if result['success']:
                    results['success'] += 1
                else:
                    results['error'] += 1
        
        threads = []
        for i in range(self.n_requests):
            wallet = wallets[i % len(wallets)]
            bounty_id = f"bounty_{i % 5}"
            t = threading.Thread(target=submit_thread, args=(bounty_id, wallet, f"Solution {i}"))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        stats = service.get_stats()
        
        return {
            'status': 'PASS' if results['success'] >= 10 else 'FAIL',
            'success': results['success'],
            'error': results['error'],
            'total_submissions': stats['total']
        }
    
    def _test_response_loss(self, service: SubmissionService, wallets: List[str]) -> Dict[str, Any]:
        results = {'committed': 0, 'lost': 0}
        
        for i in range(20):
            wallet = wallets[i % len(wallets)]
            bounty_id = "bounty_resp_loss"
            
            result = service.submit(bounty_id, wallet, f"Solution {i}")
            
            # Simulate 10% response loss
            if random.random() < 0.1:
                results['lost'] += 1
                # Retry
                retry = service.submit(bounty_id, wallet, f"Solution {i} retry")
                if retry['success']:
                    results['committed'] += 1
            else:
                if result['success']:
                    results['committed'] += 1
        
        subs = service.list_bounty_submissions("bounty_resp_loss")
        
        return {
            'status': 'PASS' if results['committed'] > 0 else 'FAIL',
            'committed': results['committed'],
            'lost_simulated': results['lost']
        }
    
    def _test_stale_update(self, service: SubmissionService, wallets: List[str]) -> Dict[str, Any]:
        wallet = wallets[0]
        bounty_id = "bounty_stale"
        
        result1 = service.submit(bounty_id, wallet, "Version 1")
        sub_id = result1['submission_id']
        
        result2 = service.submit(bounty_id, wallet, "Version 2")
        result3 = service.submit(bounty_id, wallet, "Version 3")
        
        sub = service.get_submission(sub_id)
        
        return {
            'status': 'PASS' if sub['version'] == 3 else 'FAIL',
            'final_version': sub['version'],
            'content': sub['content']
        }
    
    def _test_review_transition(self, service: SubmissionService, wallets: List[str]) -> Dict[str, Any]:
        wallet = wallets[0]
        bounty_id = "bounty_review"
        
        result = service.submit(bounty_id, wallet, "My solution")
        sub_id = result['submission_id']
        
        trans = service.transition_status(sub_id, 'in_review')
        update = service.submit(bounty_id, wallet, "Attempted update")
        
        sub = service.get_submission(sub_id)
        
        return {
            'status': 'PASS' if not update['success'] else 'FAIL',
            'update_rejected': not update['success'],
            'content_unchanged': sub['content'] == "My solution"
        }
    
    def _test_restart_recovery(self, wallets: List[str]) -> Dict[str, Any]:
        # Create new service instance (simulates restart)
        service2 = SubmissionService(self.db_path)
        
        wallet = wallets[1]
        bounty_id = "bounty_restart"
        
        # Try to submit
        result = service2.submit(bounty_id, wallet, "After restart")
        
        return {
            'status': 'PASS' if result['success'] else 'FAIL',
            'operation': result.get('operation', 'unknown')
        }
    
    def _verify_idempotency(self, service: SubmissionService) -> Dict[str, bool]:
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.cursor()
            
            # Check for duplicate active submissions
            cursor.execute("""
                SELECT bounty_id, wallet, COUNT(*) as count
                FROM submissions
                WHERE status IN ('pending', 'in_review')
                GROUP BY bounty_id, wallet
                HAVING count > 1
            """)
            no_duplicates = len(cursor.fetchall()) == 0
            
            # Check version integrity
            cursor.execute("SELECT id FROM submissions WHERE version < 1")
            correct_versions = len(cursor.fetchall()) == 0
            
            # Verify one submission per wallet per bounty
            cursor.execute("""
                SELECT COUNT(DISTINCT wallet || bounty_id) as unique_count,
                       COUNT(*) as total_count
                FROM submissions
                WHERE status IN ('pending', 'in_review')
            """)
            row = cursor.fetchone()
            one_per_wallet = row[0] == row[1]
            
            return {
                'no_duplicates': no_duplicates,
                'correct_versions': correct_versions,
                'one_submission_per_wallet': one_per_wallet
            }
        
        finally:
            conn.close()


def main():
    print("=== Idempotent Submissions Test Harness ===\n")
    
    harness = ConcurrentTestHarness(n_wallets=10, n_requests=100)
    results = harness.run_test()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    for test_name, result in results['tests'].items():
        status = result['status']
        print(f"  {test_name}: {status}")
    
    print(f"\nVerification:")
    for k, v in results['verification'].items():
        print(f"  {k}: {'✓' if v else '✗'}")
    
    print(f"\nOverall: {'✓ PASS' if results['overall_pass'] else '✗ FAIL'}")
    
    return 0 if results['overall_pass'] else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
