#!/bin/bash
# Agent Prompt-Injection Boundary Benchmark - Bounty #12
# One-command runner

set -e

cd "$(dirname "$0")"

echo "=== Agent Prompt-Injection Boundary Benchmark ==="
echo "Bounty #12 - 32 Attack Fixtures + 10 Benign Controls"
echo ""

# Run benchmark
python3 benchmark_runner.py

echo ""
echo "=== Benchmark Complete ==="
echo "Results: benchmark_report.json"
