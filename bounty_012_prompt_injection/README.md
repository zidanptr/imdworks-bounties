# Bounty #12: Agent Prompt-Injection Boundary Benchmark

**Reward:** 1 USDG  
**Deadline:** 2026-10-14T09:54:30.000Z  
**Category:** Security

## Objective
Create an offline benchmark for an agent that reads untrusted bounty text. Design a policy boundary between task content and tool authority.

## Requirements
- **30+ attack fixtures**: tool-output injection, encoded instructions, forged system messages, credential-exfiltration requests
- **10 benign controls**
- Deterministic pass/fail results
- Fail-closed tool authorization
- Machine-readable report
- Show naive baseline fails
- Defended runner blocks unauthorized calls without rejecting benign tasks
- Explain limits of deterministic benchmark
- No external sites, no real model API keys

## Deliverables
- Attack fixtures (30+)
- Benign controls (10)
- Baseline runner (naive, vulnerable)
- Defended runner (fail-closed)
- Benchmark executor
- Results report
- Threat model notes
