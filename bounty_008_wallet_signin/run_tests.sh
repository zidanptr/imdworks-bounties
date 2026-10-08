#!/bin/bash
# Wallet Sign-In Regression Suite - Bounty #8
# One-command runner

set -e

cd "$(dirname "$0")"

echo "=== Wallet Sign-In Regression Suite ==="
echo "Bounty #8 - 20+ Adversarial Test Cases"
echo ""

# Check for venv
if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install eth_account
fi

echo "Running regression suite..."
echo ""

# Run main test suite
.venv/bin/python test_suite.py

echo ""
echo "=== Demonstrating Vulnerable Implementations ==="
echo ""

echo "--- Vulnerable V1: No Nonce Tracking ---"
.venv/bin/python vulnerable_v1_no_nonce.py

echo ""
echo "--- Vulnerable V2: No Origin Binding ---"
.venv/bin/python vulnerable_v2_no_origin.py

echo ""
echo "=== All Tests Complete ==="
