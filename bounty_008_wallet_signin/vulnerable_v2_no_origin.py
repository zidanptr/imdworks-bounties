#!/usr/bin/env python3
"""
Vulnerable Wallet Sign-In Implementation #2 - Bounty #8
VULNERABILITY: No origin binding - allows CSRF attacks
"""

import time
import secrets
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


class VulnerableSignInV2:
    """
    VULNERABLE IMPLEMENTATION - DO NOT USE IN PRODUCTION
    
    Vulnerability: No origin binding
    - Does not include origin in signed message
    - Allows CSRF attacks from malicious sites
    - Signature can be used on any origin
    """
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.challenges: Dict[str, dict] = {}
        self.used_nonces: set = set()
    
    def create_challenge(self, wallet: str, origin: str = "https://localhost",
                         chain_id: int = 1) -> tuple:
        """Create a challenge (NO ORIGIN IN MESSAGE)."""
        challenge_id = secrets.token_hex(16)
        nonce = secrets.token_hex(16)
        
        # VULNERABILITY: Origin NOT included in message
        # User doesn't sign which site they're authenticating to
        message = f"""Sign to authenticate.

Wallet: {wallet}
Nonce: {nonce}

This signature authorizes authentication."""
        # MISSING: Origin binding
        # MISSING: Chain ID binding
        
        self.challenges[challenge_id] = {
            'wallet': to_checksum_address(wallet),
            'message': message,
            'nonce': nonce,
            'origin': origin,  # Stored but not in message!
            'chain_id': chain_id,
            'expires_at': time.time() + 300
        }
        
        return challenge_id, message
    
    def verify_signature(self, challenge_id: str, signature: str,
                         provided_origin: str = None) -> Session:
        """Verify signature (NO ORIGIN VERIFICATION)."""
        if challenge_id not in self.challenges:
            raise ValueError("Invalid challenge")
        
        challenge = self.challenges[challenge_id]
        
        # Check expiry
        if time.time() > challenge['expires_at']:
            raise ValueError("Challenge expired")
        
        # Check nonce reuse
        if challenge['nonce'] in self.used_nonces:
            raise ValueError("Nonce already used")
        
        # Recover signer
        message_hash = encode_defunct(text=challenge['message'])
        recovered = Account.recover_message(message_hash, signature=signature)
        recovered = to_checksum_address(recovered)
        
        # Check signer
        if recovered.lower() != challenge['wallet'].lower():
            raise ValueError("Wrong signer")
        
        # VULNERABILITY: No origin verification!
        # provided_origin is ignored
        # Attacker can use signature from any origin
        
        # Mark nonce used
        self.used_nonces.add(challenge['nonce'])
        
        # Create session
        session_id = secrets.token_hex(16)
        session = Session(
            id=session_id,
            wallet=recovered,
            created_at=time.time()
        )
        self.sessions[session_id] = session
        
        return session


if __name__ == '__main__':
    if not HAS_ETH_ACCOUNT:
        print("Install eth_account first")
        exit(1)
    
    print("=== Vulnerable Implementation V2 ===")
    print("VULNERABILITY: No origin binding - allows CSRF attacks\n")
    
    from eth_account import Account
    
    # Generate test wallet
    account = Account.create()
    wallet = account.address
    privkey = account.key.hex()
    
    print(f"Test wallet: {wallet}\n")
    
    service = VulnerableSignInV2()
    
    # Legitimate user signs on app.example.com
    print("Legitimate sign-in on app.example.com:")
    challenge_id, message = service.create_challenge(wallet, origin="https://app.example.com")
    print(f"Message (notice NO origin):\n{message}\n")
    
    message_hash = encode_defunct(text=message)
    sig = account.sign_message(message_hash)
    signature = sig.signature.hex()
    
    print(f"User signs: {signature[:20]}...{signature[-20:]}\n")
    
    # But signature doesn't include origin, so...
    print("Attacker creates malicious site evil.com")
    print("Attacker reuses the signature:\n")
    
    try:
        # VULNERABILITY: Signature works on evil.com too!
        session = service.verify_signature(challenge_id, signature,
                                           provided_origin="https://evil.com")
        print(f"  ✗ VULNERABLE! Signature from app.example.com worked on evil.com!")
        print(f"  Session created: {session.id}")
        print(f"\n  The message didn't include origin, so signature is valid anywhere!\n")
    except ValueError as e:
        print(f"  ✓ CSRF blocked: {e}")
