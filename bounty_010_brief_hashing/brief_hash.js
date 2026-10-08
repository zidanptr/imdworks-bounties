/**
 * Canonical Brief Hashing - JavaScript Implementation - Bounty #10
 * Deterministic serialization and keccak256 hashing for bounty briefs.
 */

const { keccak256 } = require('js-sha3');

// Required fields in alphabetical order
const REQUIRED_FIELDS = ['title', 'description', 'criteria', 'reward', 'token', 'deadline'];
const OPTIONAL_FIELDS = ['repo_url', 'category', 'owner'];

/**
 * Normalize string for canonical representation.
 * Rules:
 * - NFC normalization
 * - LF line endings (convert CRLF)
 * - No trailing whitespace per line
 */
function normalizeString(s) {
    if (typeof s !== 'string') {
        throw new Error(`Expected string, got ${typeof s}`);
    }
    
    // NFC normalization (Node.js strings are UTF-16, need to normalize)
    let normalized = s.normalize('NFC');
    
    // Convert CRLF to LF
    normalized = normalized.replace(/\r\n/g, '\n');
    
    // Remove trailing whitespace from each line
    normalized = normalized.split('\n').map(line => line.trimEnd()).join('\n');
    
    // Remove trailing newlines
    normalized = normalized.trimEnd();
    
    return normalized;
}

/**
 * Validate brief structure.
 */
function validateBrief(brief) {
    if (typeof brief !== 'object' || brief === null || Array.isArray(brief)) {
        throw new Error(`Expected object, got ${typeof brief}`);
    }
    
    // Check required fields
    const missing = REQUIRED_FIELDS.filter(f => !(f in brief));
    if (missing.length > 0) {
        throw new Error(`Missing required fields: ${missing.join(', ')}`);
    }
    
    // Validate types
    for (const field of REQUIRED_FIELDS) {
        if (typeof brief[field] !== 'string') {
            throw new Error(`Field '${field}' must be string, got ${typeof brief[field]}`);
        }
    }
    
    // Validate reward is numeric
    if (isNaN(parseFloat(brief.reward))) {
        throw new Error(`Field 'reward' must be numeric string, got: ${brief.reward}`);
    }
    
    // Validate deadline is ISO 8601
    const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
    if (!isoPattern.test(brief.deadline)) {
        throw new Error(`Field 'deadline' must be ISO 8601 format, got: ${brief.deadline}`);
    }
}

/**
 * Serialize brief to canonical JSON string.
 * 
 * Canonical rules:
 * 1. Only include required + present optional fields
 * 2. Fields in alphabetical order
 * 3. No extra whitespace
 * 4. UTF-8 encoding
 * 5. Strings normalized (NFC, LF line endings)
 */
function serializeBrief(brief, strict = true) {
    if (strict) {
        validateBrief(brief);
    }
    
    const canonical = {};
    
    // Add all required fields (normalized)
    const sortedRequired = [...REQUIRED_FIELDS].sort();
    for (const field of sortedRequired) {
        canonical[field] = normalizeString(brief[field]);
    }
    
    // Add optional fields if present
    const sortedOptional = [...OPTIONAL_FIELDS].sort();
    for (const field of sortedOptional) {
        if (field in brief && brief[field] !== null && brief[field] !== undefined) {
            canonical[field] = normalizeString(brief[field]);
        }
    }
    
    // Serialize to JSON with no extra whitespace
    // In JavaScript, JSON.stringify with no indent uses minimal whitespace
    // But we need to ensure consistent key ordering
    const orderedKeys = Object.keys(canonical).sort();
    const ordered = {};
    for (const key of orderedKeys) {
        ordered[key] = canonical[key];
    }
    
    return JSON.stringify(ordered);
}

/**
 * Compute keccak256 hash of canonical brief serialization.
 */
function hashBrief(brief, strict = true) {
    const canonical = serializeBrief(brief, strict);
    
    // Encode to UTF-8 bytes
    const encoder = new TextEncoder();
    const data = encoder.encode(canonical);
    
    // Compute keccak256
    const hashHex = keccak256(data);
    
    return '0x' + hashHex;
}

/**
 * Cross-language test vectors.
 */
const TEST_VECTORS = [
    {
        brief: {
            title: "Test Bounty",
            description: "Simple test case",
            criteria: "Pass all tests",
            reward: "1",
            token: "USDG",
            deadline: "2026-10-14T09:54:30.000Z"
        }
    },
    {
        brief: {
            title: "Unicode Test \u00e9\u00e8\u00ea",
            description: "Testing NFC normalization: caf\u00e9",
            criteria: "Handle Unicode correctly",
            reward: "5.5",
            token: "ETH",
            deadline: "2026-10-15T00:00:00.000Z"
        }
    },
    {
        brief: {
            title: "With Optional Fields",
            description: "Brief with repo_url",
            criteria: "Complete implementation",
            reward: "10",
            token: "USDG",
            deadline: "2026-10-20T12:00:00.000Z",
            repo_url: "https://github.com/example/repo",
            category: "Development"
        }
    },
    {
        brief: {
            title: "Line Ending Test",
            description: "Line1\r\nLine2\r\nLine3",
            criteria: "Normalize CRLF to LF",
            reward: "1",
            token: "USDG",
            deadline: "2026-10-14T00:00:00.000Z"
        }
    },
    {
        brief: {
            title: "Trailing Whitespace",
            description: "Text with trailing spaces   ",
            criteria: "Remove trailing whitespace  ",
            reward: "2",
            token: "USDG",
            deadline: "2026-10-14T00:00:00.000Z"
        }
    }
];

/**
 * Generate additional test vectors.
 */
function generateTestVectors(n = 50) {
    const vectors = [...TEST_VECTORS];
    
    // Categories and tokens
    const categories = ['Development', 'Security', 'Data', 'Research', 'Smart contracts'];
    const tokens = ['USDG', 'ETH', 'IMDBTY'];
    
    // Seeded random for reproducibility
    let seed = 20261008;
    function seededRandom() {
        seed = (seed * 9301 + 49297) % 233280;
        return seed / 233280;
    }
    
    function randomString(length) {
        const chars = 'abcdefghijklmnopqrstuvwxyz ';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars[Math.floor(seededRandom() * chars.length)];
        }
        return result.trim();
    }
    
    function randomInt(min, max) {
        return Math.floor(seededRandom() * (max - min + 1)) + min;
    }
    
    while (vectors.length < n) {
        const brief = {
            title: randomString(randomInt(10, 50)),
            description: Array.from({length: randomInt(5, 15)}, () => randomString(randomInt(5, 15))).join(' '),
            criteria: Array.from({length: randomInt(5, 10)}, () => randomString(randomInt(5, 10))).join(' '),
            reward: (seededRandom() * 100).toFixed(6),
            token: tokens[Math.floor(seededRandom() * tokens.length)],
            deadline: `2026-10-${String(randomInt(15, 28)).padStart(2, '0')}T${String(randomInt(0, 23)).padStart(2, '0')}:${String(randomInt(0, 59)).padStart(2, '0')}:${String(randomInt(0, 59)).padStart(2, '0')}.000Z`
        };
        
        if (seededRandom() > 0.5) {
            brief.category = categories[Math.floor(seededRandom() * categories.length)];
        }
        
        vectors.push({ brief });
    }
    
    return vectors;
}

// Main
if (require.main === module) {
    console.log("=== Canonical Brief Hashing - JavaScript ===\n");
    
    console.log("Test Vectors:\n");
    TEST_VECTORS.forEach((tv, i) => {
        const brief = tv.brief;
        const canonical = serializeBrief(brief);
        const hash = hashBrief(brief);
        
        console.log(`Vector ${i + 1}:`);
        console.log(`  Title: ${brief.title.substring(0, 30)}...`);
        console.log(`  Canonical: ${canonical.substring(0, 80)}...`);
        console.log(`  Hash: ${hash}`);
        console.log();
    });
    
    console.log("\nGenerating 50 test vectors...");
    const vectors = generateTestVectors(50);
    console.log(`Generated ${vectors.length} vectors\n`);
    
    console.log("Hashing all vectors...");
    vectors.forEach((v, i) => {
        const h = hashBrief(v.brief);
        if ((i + 1) % 10 === 0) {
            console.log(`  ${i + 1}/${vectors.length}: ${h.substring(0, 20)}...${h.substring(h.length - 20)}`);
        }
    });
    
    console.log(`\nAll ${vectors.length} vectors hashed successfully`);
}

module.exports = { serializeBrief, hashBrief, normalizeString, validateBrief, generateTestVectors };
