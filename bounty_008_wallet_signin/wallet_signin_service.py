#!/usr/bin/env python3
"""
Wallet Sign-In Service - Bounty #8
Local test service for nonce-bound personal_sign authentication.
"""

import os
import time
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# Use eth_account for wallet operations (pure Python, no external node required)
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from eth_utils import to_checksum_address
    HAS_ETH_ACCOUNT = True
except ImportError:
    HAS_ETH_ACCOUNT = False
    print("WARNING: eth_account not installed. Install with: pip install eth_account")


@dataclass
class Challenge:
    """Sign-in challenge."""
    id: str
    wallet: str
    message: str
    nonce: str
    origin: str
    chain_id: int
    expires_at: float
    used: bool = False


@dataclass
class Session:
    """Authenticated session."""
    id: str
    wallet: str
    origin: str
    chain_id: int
    created_at: float
    expires_at: float


class WalletSignInService:
    """
    Secure wallet sign-in service using nonce-bound personal_sign.
    
    Security properties:
    1. Nonce is single-use (replay protection)
    2. Signature bound to origin (CSRF protection)
    3. Signature bound to chain ID (cross-chain protection)
    4. Challenge expires (time window protection)
    5. Concurrent verification fails on second attempt (race condition protection)
    """
    
    DEFAULT_EXPIRY_SECONDS = 300  # 5 minutes
    DEFAULT_SESSION_EXPIRY_SECONDS = 3600  # 1 hour
    
    def __init__(self, expiry_seconds: int = None, session_expiry_seconds: int = None):
        self.challenges: Dict[str, Challenge] = {}
        self.sessions: Dict[str, Session] = {}
        self.nonces: Dict[str, str] = {}  # nonce -> challenge_id
        self.expiry_seconds = expiry_seconds or self.DEFAULT_EXPIRY_SECONDS
        self.session_expiry_seconds = session_expiry_seconds or self.DEFAULT_SESSION_EXPIRY_SECONDS
        self._lock_nonce = {}  # For concurrent verification protection
    
    def create_challenge(self, wallet: str, origin: str = "https://localhost", 
                         chain_id: int = 1) -> Tuple[str, str]:
        """
        Create a sign-in challenge for a wallet.
        
        Args:
            wallet: Ethereum address (0x...)
            origin: Expected origin (e.g., "https://localhost")
            chain_id: Expected chain ID
        
        Returns:
            (challenge_id, message_to_sign)
        """
        if not HAS_ETH_ACCOUNT:
            raise RuntimeError("eth_account required. Install with: pip install eth_account")
        
        # Normalize wallet address
        wallet = to_checksum_address(wallet)
        
        # Generate unique nonce
        nonce = secrets.token_hex(16)
        
        # Generate challenge ID
        challenge_id = secrets.token_hex(16)
        
        # Create message to sign
        timestamp = datetime.utcnow().isoformat() + "Z"
        message = f"""Sign this message to authenticate.

Wallet: {wallet}
Origin: {origin}
Chain ID: {chain_id}
Nonce: {nonce}
Timestamp: {timestamp}

This signature will expire in {self.expiry_seconds} seconds."""
        
        # Store challenge
        expires_at = time.time() + self.expiry_seconds
        self.challenges[challenge_id] = Challenge(
            id=challenge_id,
            wallet=wallet,
            message=message,
            nonce=nonce,
            origin=origin,
            chain_id=chain_id,
            expires_at=expires_at
        )
        self.nonces[nonce] = challenge_id
        
        return challenge_id, message
    
    def verify_signature(self, challenge_id: str, signature: str,
                         provided_wallet: str = None, provided_origin: str = None,
                         provided_chain_id: int = None) -> Session:
        """
        Verify a signed challenge and create a session.
        
        Args:
            challenge_id: Challenge ID from create_challenge()
            signature: Ethereum signature (hex)
            provided_wallet: Wallet address (optional, uses challenge if not provided)
            provided_origin: Origin (optional, uses challenge if not provided)
            provided_chain_id: Chain ID (optional, uses challenge if not provided)
        
        Returns:
            Session object on success
        
        Raises:
            ValueError on verification failure
        """
        if not HAS_ETH_ACCOUNT:
            raise RuntimeError("eth_account required")
        
        # Check challenge exists
        if challenge_id not in self.challenges:
            raise ValueError("Invalid challenge ID")
        
        challenge = self.challenges[challenge_id]
        
        # Check expiry
        if time.time() > challenge.expires_at:
            raise ValueError("Challenge expired")
        
        # Check already used (replay protection)
        if challenge.used:
            raise ValueError("Challenge already used (nonce replay)")
        
        # Concurrent verification protection
        if challenge_id in self._lock_nonce:
            # Another verification in progress
            raise ValueError("Concurrent verification detected")
        
        self._lock_nonce[challenge_id] = True
        try:
            # Recover signer from signature
            message_hash = encode_defunct(text=challenge.message)
            recovered_address = Account.recover_message(message_hash, signature=signature)
            recovered_address = to_checksum_address(recovered_address)
            
            # Check signer matches expected wallet
            expected_wallet = provided_wallet or challenge.wallet
            if recovered_address.lower() != expected_wallet.lower():
                raise ValueError(f"Wrong signer: expected {expected_wallet}, got {recovered_address}")
            
            # Check origin matches (if provided)
            if provided_origin is not None and provided_origin != challenge.origin:
                raise ValueError(f"Origin mismatch: expected {challenge.origin}, got {provided_origin}")
            
            # Check chain ID matches (if provided)
            if provided_chain_id is not None and provided_chain_id != challenge.chain_id:
                raise ValueError(f"Chain ID mismatch: expected {challenge.chain_id}, got {provided_chain_id}")
            
            # Mark challenge as used
            challenge.used = True
            
            # Create session
            session_id = secrets.token_hex(16)
            now = time.time()
            session = Session(
                id=session_id,
                wallet=recovered_address,
                origin=challenge.origin,
                chain_id=challenge.chain_id,
                created_at=now,
                expires_at=now + self.session_expiry_seconds
            )
            self.sessions[session_id] = session
            
            # Clean up nonce
            if challenge.nonce in self.nonces:
                del self.nonces[challenge.nonce]
            
            return session
        
        finally:
            # Release lock
            if challenge_id in self._lock_nonce:
                del self._lock_nonce[challenge_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session and time.time() > session.expires_at:
            del self.sessions[session_id]
            return None
        return session
    
    def cleanup_expired(self):
        """Remove expired challenges and sessions."""
        now = time.time()
        
        # Clean challenges
        expired_challenges = [
            cid for cid, c in self.challenges.items() 
            if now > c.expires_at
        ]
        for cid in expired_challenges:
            del self.challenges[cid]
            if self.challenges[cid].nonce in self.nonces:
                del self.nonces[self.challenges[cid].nonce]
        
        # Clean sessions
        expired_sessions = [
            sid for sid, s in self.sessions.items()
            if now > s.expires_at
        ]
        for sid in expired_sessions:
            del self.sessions[sid]


def generate_test_wallet() -> Tuple[str, str]:
    """Generate a new test wallet (address, private_key)."""
    if not HAS_ETH_ACCOUNT:
        raise RuntimeError("eth_account required")
    
    account = Account.create()
    return account.address, account.key.hex()


def sign_message(private_key: str, message: str) -> str:
    """Sign a message with a private key."""
    if not HAS_ETH_ACCOUNT:
        raise RuntimeError("eth_account required")
    
    account = Account.from_key(private_key)
    message_hash = encode_defunct(text=message)
    signature = account.sign_message(message_hash)
    return signature.signature.hex()


if __name__ == '__main__':
    # Quick test
    if not HAS_ETH_ACCOUNT:
        print("Install eth_account first: pip install eth_account")
        exit(1)
    
    print("=== Wallet Sign-In Service Test ===\n")
    
    service = WalletSignInService()
    
    # Generate test wallet
    wallet, privkey = generate_test_wallet()
    print(f"Test wallet: {wallet}")
    
    # Create challenge
    challenge_id, message = service.create_challenge(wallet)
    print(f"\nChallenge ID: {challenge_id}")
    print(f"Message:\n{message}")
    
    # Sign message
    signature = sign_message(privkey, message)
    print(f"\nSignature: {signature[:20]}...{signature[-20:]}")
    
    # Verify
    try:
        session = service.verify_signature(challenge_id, signature)
        print(f"\n✓ Verification successful!")
        print(f"Session ID: {session.id}")
        print(f"Wallet: {session.wallet}")
    except ValueError as e:
        print(f"\n✗ Verification failed: {e}")
