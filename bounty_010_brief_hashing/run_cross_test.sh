#!/bin/bash
# Canonical Brief Hashing - Cross-Language Test - Bounty #10
# One-command runner

set -e

cd "$(dirname "$0")"

echo "=== Canonical Brief Hashing - Cross-Language Test ==="
echo "Bounty #10 - Python + JavaScript Implementation"
echo ""

# Check venv
if [ ! -d ".venv" ]; then
    echo "Setting up Python venv..."
    python3 -m venv .venv
    .venv/bin/pip install pycryptodome
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: node required"
    exit 1
fi

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm init -y > /dev/null 2>&1
    npm install js-sha3 > /dev/null 2>&1
fi

echo "=== Running Cross-Language Test ==="
echo ""

# Generate and compare hashes
.venv/bin/python3 << 'PYTHON_EOF'
import json
import subprocess

# Generate test vectors
from brief_hash import generate_test_vectors, hash_brief, serialize_brief

vectors = generate_test_vectors(50)

print(f"Testing {len(vectors)} vectors...")
print()

# Compute Python hashes
python_hashes = []
for i, v in enumerate(vectors):
    h = hash_brief(v['brief'])
    canonical = serialize_brief(v['brief'])
    python_hashes.append({
        'index': i,
        'hash': h,
        'canonical': canonical,
        'brief': v['brief']
    })

# Save for JavaScript
with open('test_vectors_python.json', 'w') as f:
    json.dump(python_hashes, f, indent=2)

print(f"Python: Computed {len(python_hashes)} hashes")
PYTHON_EOF

echo ""

# Run JavaScript comparison
node << 'JS_EOF'
const fs = require('fs');
const { hashBrief, serializeBrief } = require('./brief_hash.js');

// Load Python results
const pythonResults = JSON.parse(fs.readFileSync('test_vectors_python.json', 'utf8'));

console.log(`JavaScript: Computing ${pythonResults.length} hashes...`);
console.log();

let matchCount = 0;
let mismatchCount = 0;
let errors = [];

pythonResults.forEach((item, i) => {
    const jsHash = hashBrief(item.brief);
    const jsCanonical = serializeBrief(item.brief);
    
    if (jsHash === item.hash) {
        matchCount++;
        if ((i + 1) % 10 === 0) {
            console.log(`  ${i + 1}/${pythonResults.length}: MATCH ${jsHash.substring(0, 20)}...`);
        }
    } else {
        mismatchCount++;
        errors.push({
            index: i,
            python_hash: item.hash,
            js_hash: jsHash,
            python_canonical: item.canonical.substring(0, 100),
            js_canonical: jsCanonical.substring(0, 100)
        });
    }
});

console.log();
console.log("=== Results ===");
console.log(`Matches: ${matchCount}/${pythonResults.length}`);
console.log(`Mismatches: ${mismatchCount}/${pythonResults.length}`);

if (mismatchCount > 0) {
    console.log();
    console.log("=== Mismatches ===");
    errors.slice(0, 5).forEach(e => {
        console.log();
        console.log(`Index ${e.index}:`);
        console.log(`  Python: ${e.python_hash}`);
        console.log(`  JS:      ${e.js_hash}`);
        console.log(`  Python canonical: ${e.python_canonical}`);
        console.log(`  JS canonical:      ${e.js_canonical}`);
    });
    process.exit(1);
} else {
    console.log();
    console.log(`✓ All ${pythonResults.length} vectors match between Python and JavaScript`);
    
    // Save results
    const results = {
        total: pythonResults.length,
        matches: matchCount,
        mismatches: mismatchCount,
        vectors: pythonResults.map((p, i) => ({
            index: i,
            hash: p.hash,
            brief_title: p.brief.title
        }))
    };
    
    fs.writeFileSync('cross_language_results.json', JSON.stringify(results, null, 2));
    console.log('\nResults saved to cross_language_results.json');
}
JS_EOF

echo ""
echo "=== Test Complete ==="
