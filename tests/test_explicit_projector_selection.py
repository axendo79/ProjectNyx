"""ADR 0032: future/private defaults must not silently select stage two."""
import ast
import importlib
import inspect
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Exact file + qualified name, not basename or suffix matching.
LEGACY = {
    ("src/nyx/projection.py", "project"),
    *(("src/nyx/storage.py", name) for name in (
        "safe_append_event", "evaluate_whole_view", "read_belief", "read_projection_status")),
    *(("src/nyx/skeleton.py", name) for name in (
        "_record", "record_observation", "record_correction")),
}
LEGACY_ALIASES = {
    ("scripts/seed_store.py", "seed_store", "projector"),
    ("scripts/verify_store.py", "verify_store", "projector"),
}
REQUIRED_ALIASES = {
    ("src/nyx/storage.py", "_append_stage_two", "version"),
    ("src/nyx/storage.py", "_registered_projector", "version"),
    ("src/nyx/storage.py", "_snapshot_projector", "version"),
    ("src/nyx/storage.py", "_read_snapshot", "version"),
    ("src/nyx/storage.py", "_read_identity", "version"),
    ("src/nyx/storage.py", "_publish_delta", "version"),
    ("src/nyx/cli.py", "_identity_version", "version"),
    ("src/nyx/cli.py", "_replay", "version"),
    ("scripts/verify_store.py", "Report.__init__", "version"),
    ("scripts/verify_store.py", "load_projection", "version"),
    ("scripts/verify_store.py", "lineage_record", "version"),
    ("scripts/verify_store.py", "Replay.__init__", "version"),
    ("scripts/verify_store.py", "verify_connection", "version"),
}
LEGACY_PARSERS = {
    ("src/nyx/cli.py", "_parser"),
    ("scripts/seed_store.py", "main"),
    ("scripts/verify_store.py", "main"),
}


def scoped_nodes(tree, scope=()):
    for child in ast.iter_child_nodes(tree):
        nested = scope + (child.name,) if isinstance(
            child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) else scope
        yield child, ".".join(nested)
        yield from scoped_nodes(child, nested)


def parameter_defaults(node):
    positional = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + node.args.defaults
    return {arg.arg: default for arg, default in
            [*zip(positional, defaults), *zip(node.args.kwonlyargs, node.args.kw_defaults)]}


def literal_zero(node):
    return isinstance(node, ast.Constant) and node.value == "0"


def class_annotations(node):
    """Include conditional class fields, but exclude method locals/nested scopes."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(child, ast.AnnAssign):
            yield child
        yield from class_annotations(child)


def non_constructor_field(node):
    return (isinstance(node, ast.Call)
            and ast.unparse(node.func) in ("field", "dataclasses.field")
            and any(key.arg == "init" and isinstance(key.value, ast.Constant)
                    and key.value.value is False for key in node.keywords))


def violations(source, path):
    """Check declared names/aliases; review detects selectors hidden under other names."""
    errors = []
    seen_aliases = set()
    for node, name in scoped_nodes(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for param, default in parameter_defaults(node).items():
                alias = (path, name, param)
                if not isinstance(node, ast.Lambda) and alias in LEGACY_ALIASES | REQUIRED_ALIASES:
                    seen_aliases.add(alias)
                    valid = literal_zero(default) if alias in LEGACY_ALIASES else default is None
                    if not valid:
                        errors.append(f"{path}:{node.lineno} {name}: {param} alias default")
                if param == "projector_version" and default is not None:
                    if (isinstance(node, ast.Lambda) or (path, name) not in LEGACY
                            or not literal_zero(default)):
                        errors.append(f"{path}:{node.lineno} {name}: {param} default")
        if isinstance(node, ast.ClassDef):
            for field in class_annotations(node):
                if (isinstance(field.target, ast.Name) and field.target.id == "projector_version"
                        and field.value is not None and not non_constructor_field(field.value)):
                    errors.append(f"{path}:{field.lineno} {name}: projector_version field default")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            options = {key.arg: key.value for key in node.keywords}
            if node.func.attr == "add_argument":
                strings = {arg.value for arg in node.args
                           if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
                if "--projector-version" in strings:
                    required = options.get("required")
                    if ("default" in options or not isinstance(required, ast.Constant)
                            or required.value is not True):
                        errors.append(f"{path}:{node.lineno} {name}: --projector-version must be required without default")
                if "--projector" in strings:
                    if (path, name) not in LEGACY_PARSERS or not literal_zero(options.get("default")):
                        errors.append(f"{path}:{node.lineno} {name}: --projector requires legacy allowlist and literal 0")
            if node.func.attr == "set_defaults" and {"projector", "projector_version"}.intersection(options):
                errors.append(f"{path}:{node.lineno} {name}: parser set_defaults")
    for alias in sorted(LEGACY_ALIASES | REQUIRED_ALIASES):
        if alias[0] == path and alias not in seen_aliases:
            errors.append(f"{path}: missing alias {alias[1]}.{alias[2]}")
    return errors


def test_no_selectable_projector_defaults_outside_explicit_legacy_allowlist():
    errors = []
    paths = set()
    for folder in ("src", "scripts"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            paths.add(relative)
            errors.extend(violations(path.read_text(encoding="utf-8"), relative))
    assert {alias[0] for alias in LEGACY_ALIASES | REQUIRED_ALIASES} <= paths
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("source", [
    'def future(projector_version="1"): pass',
    'def _private(projector_version=PROJECTOR_VERSION): pass',
    'async def future(*, projector_version=None): pass',
    'def future(projector_version="0", /): pass',
    'def future(projector_version=choose()): pass',
    'class Future:\n def __init__(self, *, projector_version=PROJECTOR_VERSION): pass',
    'def parent():\n def hidden(projector_version="2"): pass',
    'f = lambda projector_version="1": None',
    'parser.add_argument("--projector-version", default=PROJECTOR_VERSION)',
    'parser.add_argument("--projector-version")',
    'parser.set_defaults(projector_version="1")',
])
def test_guard_rejects_new_hidden_and_constant_defaults(source):
    assert violations(source, "src/nyx/future.py")


def test_legacy_allowlist_is_exact_and_literal():
    assert not violations('def project(projector_version="0"): pass', "src/nyx/projection.py")
    assert violations('def project(projector_version=LEGACY_VERSION): pass', "src/nyx/projection.py")
    assert violations('def project(projector_version="1"): pass', "src/nyx/projection.py")
    assert violations('def outer():\n def project(projector_version="0"): pass', "src/nyx/projection.py")
    assert violations('def project(projector_version="0"): pass', "src/nyx/other.py")


@pytest.mark.parametrize("source", [
    'def schema(version=4): pass',
    'def unrelated(projector=None): pass',
    'class Schema:\n version: int = 4',
])
def test_unrelated_parameter_names_are_outside_guard(source):
    assert not violations(source, "src/nyx/future.py")


@pytest.mark.parametrize("alias", sorted(LEGACY_ALIASES | REQUIRED_ALIASES))
@pytest.mark.parametrize("change", ["default", "function_rename", "parameter_rename", "removal"])
def test_alias_defaults_and_existence_are_guarded(alias, change):
    path, name, param = alias
    source = (ROOT / path).read_text(encoding="utf-8")
    assert not violations(source, path)
    tree = ast.parse(source)
    node = next(node for node, qualified in scoped_nodes(tree)
                if qualified == name and isinstance(node, ast.FunctionDef))
    if change == "default":
        positional = node.args.posonlyargs + node.args.args
        index = next(i for i, arg in enumerate(positional) if arg.arg == param)
        # Every listed required alias has only required positional arguments.
        # Add defaults from the alias onward to retain a valid Python signature.
        node.args.defaults = [ast.Constant("1" if alias in LEGACY_ALIASES else "0")
                              for _ in positional[index:]]
    elif change == "function_rename":
        node.name += "_renamed"
    elif change == "parameter_rename":
        next(arg for arg in node.args.args if arg.arg == param).arg += "_renamed"
    else:
        for parent in ast.walk(tree):
            if hasattr(parent, "body") and isinstance(parent.body, list) and node in parent.body:
                parent.body.remove(node)
                if not parent.body:
                    parent.body.append(ast.Pass())
                break
    errors = violations(ast.unparse(tree), path)
    if change == "default":
        assert any(f"{name}: {param} alias default" in error for error in errors)
    else:
        assert f"{path}: missing alias {name}.{param}" in errors


@pytest.mark.parametrize("source", [
    'parser.add_argument("--projector-version", required=True, default=None)',
    'parser.add_argument("--projector-version", required=False)',
    'parser.add_argument("--projector", required=True)',
    'parser.add_argument("--projector", default="0")',
])
def test_parser_options_have_distinct_rules(source):
    assert violations(source, "scripts/future.py")


def test_parser_matching_is_exact_and_legacy_allowlist_is_scoped():
    assert not violations('parser.add_argument("--projector-version", required=True)', "scripts/future.py")
    assert not violations('parser.add_argument("--projector-1-max-events", default=600)', "scripts/future.py")
    assert not violations((ROOT / "scripts/probe_store_scaling.py").read_text(encoding="utf-8"),
                          "scripts/probe_store_scaling.py")
    helpers = 'def _identity_version(version): pass\ndef _replay(conn, version, as_of): pass\n'
    legacy = helpers + 'def _parser():\n parser.add_argument("--projector", default="0")'
    assert not violations(legacy, "src/nyx/cli.py")
    assert violations(legacy.replace('default="0"', 'default=LEGACY_VERSION'), "src/nyx/cli.py")
    assert violations(legacy.replace('def _parser()', 'def renamed()'), "src/nyx/cli.py")
    # Even in a legacy parser, --projector-version cannot inherit the exception.
    assert violations(legacy.replace('"--projector"', '"--projector-version"'), "src/nyx/cli.py")


@pytest.mark.parametrize("definition", [
    'projector_version: str = "1"',
    'projector_version: str = field(default="1", init=True)',
    'projector_version: str = field(default_factory=choose)',
    'projector_version: str = PROJECTOR_VERSION',
    'projector_version: str = field(default="1", init=DISABLED)',
])
def test_generated_constructor_defaults_fail(definition):
    source = '@dataclass(init=True)\nclass Future:\n ' + definition
    assert violations(source, "src/nyx/future.py")


def test_non_constructor_fields_pass_including_committed_snapshot():
    source = (ROOT / "src/nyx/committed.py").read_text(encoding="utf-8")
    assert not violations(source, "src/nyx/committed.py")
    from nyx import committed
    assert "projector_version" not in inspect.signature(committed.Snapshot).parameters
    for definition in ('projector_version: str',
                       'projector_version: str = field(default="2", init=False)',
                       'projector_version: str = dataclasses.field(default="2", init=False)'):
        assert not violations('class Future:\n ' + definition, "src/nyx/future.py")
    assert violations('class Future:\n if True:\n  projector_version: str = "1"', "src/nyx/future.py")
    assert not violations('class Future:\n def method(self):\n  projector_version: str = "1"',
                          "src/nyx/future.py")


def required_boundaries():
    """Discover actual production parameters, including newly added functions."""
    for folder in ("src/nyx", "scripts"):
        for path in sorted((ROOT / folder).glob("*.py")):
            for node, name in scoped_nodes(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                relative = path.relative_to(ROOT).as_posix()
                aliases = {param for file, qualified, param in REQUIRED_ALIASES
                           if (file, qualified) == (relative, name)}
                if not any(arg.arg in {"projector_version"} | aliases for arg in (
                        node.args.posonlyargs + node.args.args + node.args.kwonlyargs)):
                    continue
                if (path.relative_to(ROOT).as_posix(), name) in LEGACY:
                    continue
                # Module functions and constructors are actual callable entry points.
                if "." in name and not name.endswith(".__init__"):
                    continue
                module = ("nyx." if folder == "src/nyx" else "scripts.") + path.stem
                yield module, name


@pytest.mark.parametrize("module,name", list(required_boundaries()))
def test_omission_refuses_before_observable_work(module, name):
    target = importlib.import_module(module)
    for part in name.split("."):
        target = getattr(target, part)
    args, kwargs = [], {}
    for param in inspect.signature(target).parameters.values():
        if param.name in ("projector_version", "version") or param.default is not inspect.Parameter.empty:
            continue
        if param.kind == param.POSITIONAL_ONLY:
            args.append(object())
        elif param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            kwargs[param.name] = object()
    # Opaque arguments cannot open storage, iterate a log or initialize a snapshot.
    # Only argument binding can produce this missing-version refusal.
    with pytest.raises(TypeError, match="required.*(?:projector_version|version)"):
        target(*args, **kwargs)


def test_lineage_diagnostic_requires_explicit_selection():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/probe_lineage_scaling.py"),
                             "--sizes", "1", "--repeat", "1"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "required" in result.stderr and "--projector-version" in result.stderr
    assert not result.stdout


def test_legacy_defaults_remain_literal_zero():
    for path, name in LEGACY:
        module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
        target = getattr(importlib.import_module(module), name)
        defaults = {p.name: p.default for p in inspect.signature(target).parameters.values()}
        assert defaults.get("projector_version") == "0", (path, name)
