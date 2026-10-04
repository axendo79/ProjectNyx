"""ADR 0032 naming inventory, including selectors forwarded by script wrappers."""
import ast
from pathlib import Path

import pytest

from test_explicit_projector_selection import LEGACY_ALIASES, REQUIRED_ALIASES, ROOT, scoped_nodes


def forwarded_version_inventory(sources):
    """Resolve imports and positional/keyword selector arguments to a fixed point.

    Seed with projector_version and the ADR's exact grandfathered aliases.
    Discover wrappers by forwarding, rather than treating unrelated version
    parameters as selectors. Constructor positions exclude self.
    """
    functions, imports, selectors = {}, {}, {}
    aliases = LEGACY_ALIASES | REQUIRED_ALIASES
    for path, source in sources.items():
        module = path.removeprefix('src/').removesuffix('.py').replace('/', '.')
        if path.startswith('scripts/'):
            module = Path(path).stem
        tree = ast.parse(source)
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for item in node.names:
                    imported[item.asname or item.name] = f'{node.module}.{item.name}'
            elif isinstance(node, ast.Import):
                for item in node.names:
                    imported[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        imports[module] = imported
        for node, name in scoped_nodes(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            symbol = f'{module}.{name.removesuffix(".__init__")}'
            positional = [arg.arg for arg in node.args.posonlyargs + node.args.args]
            if positional and positional[0] in ('self', 'cls'):
                positional = positional[1:]
            params = positional + [arg.arg for arg in node.args.kwonlyargs]
            functions[symbol] = (path, name, node, module, positional, params)
            selectors[symbol] = {param for param in params if param == 'projector_version' or (path, name, param) in aliases}

    found = set()
    changed = True
    while changed:
        changed = False
        for symbol, (path, name, node, module, positional, params) in functions.items():
            if 'version' not in params:
                continue
            for call in (child for child in ast.walk(node) if isinstance(child, ast.Call)):
                target = ast.unparse(call.func)
                head, _, tail = target.partition('.')
                target = imports[module].get(head, f'{module}.{head}') + (f'.{tail}' if tail else '')
                if target not in functions:
                    continue
                target_positional = functions[target][4]
                arguments = dict(zip(target_positional, call.args))
                arguments.update((key.arg, key.value) for key in call.keywords if key.arg)
                if any(isinstance(arguments.get(param), ast.Name) and arguments[param].id == 'version'
                       for param in selectors[target]):
                    found.add((path, name, 'version'))
                    if 'version' not in selectors[symbol]:
                        selectors[symbol].add('version')
                        changed = True
    return sorted(item for item in found if item[0].startswith('scripts/'))


def test_script_version_parameters_forwarded_to_projector_apis_are_grandfathered():
    sources = {path.relative_to(ROOT).as_posix(): path.read_text(encoding='utf-8')
               for folder in ('src', 'scripts') for path in (ROOT / folder).rglob('*.py')}
    inventory = forwarded_version_inventory(sources)
    unexpected = [item for item in inventory if item not in REQUIRED_ALIASES]
    assert not unexpected, f'Projector-selecting version parameters outside ADR 0032 inventory: {unexpected}\nFull inventory: {inventory}'


def test_reviewed_script_selectors_use_projector_version():
    expected = {
        'verify_store': ('check_freshness',),
        'replay_campaign': ('generate', 'prepare', 'publication', 'assert_equivalent', 'build', 'exercise'),
        'crash_campaign': ('child', 'exercise'),
        'mutation_campaign': ('mutate', 'classify', 'cases'),
    }
    errors = []
    for module, names in expected.items():
        nodes = dict((node.name, node) for node in ast.parse((ROOT / f'scripts/{module}.py').read_text(encoding='utf-8')).body
                     if isinstance(node, ast.FunctionDef))
        for name in names:
            params = {arg.arg for arg in nodes[name].args.args + nodes[name].args.kwonlyargs}
            if 'projector_version' not in params or 'version' in params:
                errors.append(f'{module}.{name}: {sorted(params)}')
    assert not errors, '\n'.join(errors)


@pytest.mark.parametrize('argument,selected', [
    ('conn, version', True), ('conn, projector_version=version', True),
    ('version, "1"', False), ('conn, "1"', False),
])
def test_forwarding_inventory_tracks_selector_position_and_import_aliases(argument, selected):
    sources = {
        'src/nyx/storage.py': 'def api(conn, projector_version): pass',
        'scripts/future.py': f'from nyx import storage as db\ndef wrapper(conn, version):\n db.api({argument})\n',
    }
    assert bool(forwarded_version_inventory(sources)) == selected


def test_forwarding_inventory_discovers_transitive_wrappers():
    sources = {
        'src/nyx/storage.py': 'def api(conn, projector_version): pass',
        'scripts/future.py': 'from nyx.storage import api as selected\ndef outer(conn, version):\n inner(conn, version)\ndef inner(conn, version):\n selected(conn, version)\n',
    }
    assert forwarded_version_inventory(sources) == [
        ('scripts/future.py', 'inner', 'version'), ('scripts/future.py', 'outer', 'version')]
