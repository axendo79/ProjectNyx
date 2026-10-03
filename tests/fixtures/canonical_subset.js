// Test-only independent Node oracle for the bounded subset documented in the
// Python test. It does not define production JSON admission or a private codec.
const fs = require('node:fs');
const crypto = require('node:crypto');

function codePointOrder(left, right) {
  const a = Array.from(left, char => char.codePointAt(0));
  const b = Array.from(right, char => char.codePointAt(0));
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return a.length - b.length;
}

function canonical(value) {
  if (value === null) return 'null';
  if (typeof value === 'boolean' || typeof value === 'string') {
    return JSON.stringify(value);
  }
  if (typeof value === 'number' && Number.isSafeInteger(value)) return String(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (typeof value === 'object') {
    return '{' + Object.keys(value).sort(codePointOrder)
      .map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  throw new Error('value outside evidence subset');
}

const values = JSON.parse(fs.readFileSync(0, 'utf8'));
const rows = values.map(value => {
  const bytes = canonical(value);
  return {canonical: bytes, sha256: crypto.createHash('sha256').update(bytes, 'utf8').digest('hex')};
});
process.stdout.write(JSON.stringify(rows));
