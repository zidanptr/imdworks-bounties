#!/usr/bin/env python3
"""
Vulnerable Wallet Sign-In Implementation #1 - Bounty #8
VULNERABILITY: No nonce tracking - allows replay attacks
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from eth_utils import to_checksum_address
    HAS_ETH_ACCOUNT = True
except ImportError:
    HAS_ETH_ACCOUNT = False


@dataclass
class Session:
    id: str
    wallet: str
    created_at: float


class VulnerableSignInV1:
    """
    VULNERABLE IMPLEMENTATION - DO NOT USE IN PRODUCTION
    
    Vulnerability: No nonce tracking
    - Does not track used challenges
    - Allows signature replay attacks
    - Same signature can be verified multiple times
    """
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.challenges: Dict[str, dict] = {}
    
    def create_challenge(self, wallet: str, origin: str = "https://localhost",
                         chain_id: int = 1) -> tuple:
        """Create a challenge (NO NONCE TRACKING)."""
        import secrets
        challenge_id = secrets.token_hex(16)
        
        # Vulnerability: No unique nonce enforced
        message = f"Sign to authenticate.\nWallet: {wallet}\nChallenge: {challenge_id}"
        
        self.challenges[challenge_id] = {
            'wallet': to_checksum_address(wallet),
            'message': message,
            'origin': origin,
            'chain_id': chain_id,
            # MISSING: nonce tracking
            # MISSING: expiry tracking
        }
        
        return challenge_id, message
    
    def verify_signature(self, challenge_id: str, signature: str) -> Session:
        """Verify signature (NO REPLAY PROTECTION)."""
        if challenge_id not in self.challenges:
            raise ValueError("Invalid challenge")
        
        challenge = self.challenges[challenge_id]
        
        # Recover signer
        message_hash = encode_defunct(text=challenge['message'])
        recovered = Account.recover_message(message_hash, signature=signature)
        recovered = to_checksum_address(recovered)
        
        # Check signer
        if recovered.lower() != challenge['wallet'].lower():
            raise ValueError("Wrong signer")
        
        # VULNERABILITY: No check if challenge already used
        # VULNERABILITY: Challenge can be replayed infinitely
        
        # Create session
        import secrets
        session_id = secrets.token_hex(16)
        session = Session(
            id=session_id,
            wallet=recovered,
            created_at=time.time()
        )
        self.sessions[session_id] = session
        
        # VULNERABILITY: Challenge NOT marked as used
        # Can be verified again!
        
        return session


if __name__ == '__main__':
    if not HAS_ETH_ACCOUNT:
        print("Install eth_account first")
        exit(1)
    
    print("=== Vulnerable Implementation V1 ===")
    print("VULNERABILITY: No nonce tracking - allows replay attacks\n")
    
    from eth_account import Account
    
    # Generate test wallet
    account = Account.create()
    wallet = account.address
    privkey = account.key.hex()
    
    print(f"Test wallet: {wallet}\n")
    
    service = VulnerableSignInV1()
    
    # Create challenge
    challenge_id, message = service.create_challenge(wallet)
    print(f"Challenge ID: {challenge_id}")
    print(f"Message: {message}\n")
    
    # Sign
    message_hash = encode_defunct(text=message)
    sig = account.sign_message(message_hash)
    signature = sig.signature.hex()
    
    # First verification
    print("First verification:")
    session1 = service.verify_signature(challenge_id, signature)
    print(f"  ✓ Success! Session: {session1.id}\n")
    
    # Replay attack
    print("REPLAY ATTACK - Using same signature again:")
    try:
        session2 = service.verify_signature(challenge_id, signature)
        print(f"  ✗ VULNERABLE! Replay succeeded! Session: {session2.id}")
        print(f"  \nThis should have been rejected!\n")
    except ValueError as e:
        print(f"  ✓ Replay blocked: {e}")
