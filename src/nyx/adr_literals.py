"""ADR 0031 section 8(f): literal declarations, never inferred ADR authority."""
import re


class LiteralExtractionError(ValueError):
    """The entire artifact refuses; callers prepare no partial requests."""


PREFIXES = {
    '# ': 'adr.title.literal',
    'Status: ': 'adr.status.literal',
    '- **Status:** ': 'adr.status.literal',
    'Implementation: ': 'adr.implementation.literal',
    '- **Implementation:** ': 'adr.implementation.literal',
}
CANDIDATE = re.compile(r'^(?:- )?(?:\*\*)?(Status|Implementation)(?:\*\*)?:')
HEADING = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')


def _body(raw):
    return raw.removesuffix(b'\n').removesuffix(b'\r')


def extract_literals(data):
    """Return ordered {property_id, value, location} records over unmodified bytes."""
    if not isinstance(data, bytes): raise TypeError('pinned artifact must be bytes')
    if data.startswith(b'\xef\xbb\xbf'): raise LiteralExtractionError('UTF-8 BOM refuses')
    try: data.decode('utf-8', errors='strict')
    except UnicodeError as exc: raise LiteralExtractionError('invalid UTF-8') from exc
    raw_lines = data.splitlines(keepends=True)
    lines = [_body(raw).decode('utf-8') for raw in raw_lines]
    offsets, offset = [], 0
    for raw in raw_lines:
        offsets.append(offset); offset += len(raw)
    declarations, seen, fence = [], set(), None
    for index, line in enumerate(lines):
        marker = FENCE.match(line)
        if fence is not None:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                    and not marker[2].strip()):
                fence = None
            continue
        if marker:
            fence = marker[1][0], len(marker[1])
            continue
        prefix = next((p for p in PREFIXES if line.startswith(p)), None)
        if prefix is None:
            if CANDIDATE.match(line):
                raise LiteralExtractionError(f'line {index + 1}: unsupported declaration markup/delimiter')
            continue
        prop = PREFIXES[prefix]
        if prop in seen: raise LiteralExtractionError(f'line {index + 1}: repeated {prop}')
        seen.add(prop)
        if line[len(prefix):] == '': raise LiteralExtractionError(f'line {index + 1}: empty explicit value')
        declarations.append((index, prefix, prop))
    if fence is not None: raise LiteralExtractionError('unclosed code fence')
    result = []
    for index, prefix, prop in declarations:
        last = index
        for following in range(index + 1, len(lines)):
            line = lines[following]
            if not line.strip() or HEADING.match(line) or line.startswith('- '): break
            if any(d[0] == following for d in declarations):
                raise LiteralExtractionError(f'line {following + 1}: overlapping ambiguous declarations')
            last = following
        start = offsets[index] + len(prefix.encode('utf-8'))
        end = offsets[last] + len(_body(raw_lines[last]))
        result.append({'property_id': prop, 'value': data[start:end].decode('utf-8'),
                       'location': {'start_line': index + 1, 'end_line': last + 1,
                                    'start_byte': start, 'end_byte': end}})
    return result
