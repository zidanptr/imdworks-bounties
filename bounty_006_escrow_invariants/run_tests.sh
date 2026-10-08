#!/bin/bash
# Escrow Invariant Harness - Bounty #6
# One-command runner for Foundry tests

set -e

echo "=== Escrow Invariant Harness - Bounty #6 ==="
echo ""

cd "$(dirname "$0")"

# Check foundry
if ! command -v forge &> /dev/null; then
    echo "Installing Foundry..."
    curl -L https://foundry.paradigm.xyz | bash
    source ~/.bashrc
    foundryup
fi

# Build
echo "Building contracts..."
forge build

echo ""
echo "=== Running Tests ==="
echo ""

# Run all tests
forge test -vvv

echo ""
echo "=== Running Fuzz Tests ==="
forge test --match-test testFuzz -vv

echo ""
echo "=== Running Invariant Tests ==="
forge test --match-test invariant -vv

echo ""
echo "=== Coverage Report ==="
forge coverage --report summary

echo ""
echo "=== Tests Complete ==="
