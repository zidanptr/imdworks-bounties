#!/bin/bash
# USDG Parser Bounty #9 - One-command runner
# Usage: ./run_tests.sh

set -e

echo "=== USDG Parser Bounty #9 ==="
echo "Running 100,000+ seeded test cases..."
echo ""

cd "$(dirname "$0")"

# Run test suite
python3 test_generator.py

echo ""
echo "=== Test Complete ==="
echo "Results: test_results.json"
echo ""
echo "To parse a value manually:"
echo "  python3 usdg_parser.py '123.456789'"
