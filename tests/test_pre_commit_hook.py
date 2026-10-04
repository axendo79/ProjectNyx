"""Exercise the tracked hook in disposable repositories, never this index."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def discover_bash(git, *, windows=os.name == 'nt'):
    candidates = [shutil.which('bash')]
    if windows:
        git_path = Path(git).resolve()
        if git_path.parent.name.lower() == 'cmd':
            install_root = git_path.parents[1]
        elif (git_path.parent.name.lower() == 'bin' and
              git_path.parents[1].name.lower() == 'mingw64'):
            install_root = git_path.parents[2]
        else:
            install_root = None
        if install_root is not None:
            candidates.extend(install_root / name for name in ('bin/bash.exe', 'usr/bin/bash.exe'))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            # Windows PATH can expose the WSL launcher named bash.exe. A Linux
            # shell cannot run this Windows fixture's interpreter/path layout.
            try:
                probe = subprocess.run([str(candidate), '--version'], capture_output=True,
                                       timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if (probe.returncode == 0 and b'GNU bash' in probe.stdout and
                    not (windows and b'pc-linux' in probe.stdout)):
                return str(candidate)
    return None


@pytest.fixture
def hook_repo(tmp_path):
    git = shutil.which('git')
    assert git is not None, 'Git is required to exercise the pre-commit hook'
    bash = discover_bash(git)
    if bash is None:
        pytest.skip('No usable Bash found on PATH or in Git bin/usr/bin (cmd/mingw64 layouts)')
    subprocess.run([git, 'init', '--quiet', str(tmp_path)], check=True)
    (tmp_path / '.githooks').mkdir()
    shutil.copyfile(ROOT / '.githooks/pre-commit', tmp_path / '.githooks/pre-commit')
    (tmp_path / 'scripts').mkdir()
    # This checker double records invocation, exact flags and interpreter mode.
    (tmp_path / 'scripts/check_docs.py').write_text(
        'from pathlib import Path\nimport sys\n'
        'assert sys.argv[1:] == ["--fix-none"]\n'
        'assert sys.dont_write_bytecode\n'
        'Path("checked").write_text("checked")\n'
        'sys.exit(1 if Path("docs-fail").exists() else 0)\n', encoding='utf-8')
    # Supply the current interpreter without relying on the shell's Python PATH.
    interpreter = tmp_path / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text('#!/bin/bash\nexec "' + Path(sys.executable).as_posix() + '" "$@"\n',
                           encoding='utf-8', newline='\n')
    interpreter.chmod(0o755)
    return tmp_path, git, str(bash)


@pytest.mark.parametrize('layout', ['cmd/git.exe', 'mingw64/bin/git.exe'])
@pytest.mark.parametrize('bash_location', ['bin/bash.exe', 'usr/bin/bash.exe'])
def test_discovery_handles_git_layouts_without_path_bash(tmp_path, monkeypatch, layout, bash_location):
    git = tmp_path / layout
    bash = tmp_path / bash_location
    git.parent.mkdir(parents=True)
    git.touch()
    bash.parent.mkdir(parents=True, exist_ok=True)
    bash.touch()
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, b'GNU bash fixture', b''))
    assert discover_bash(git, windows=True) == str(bash)


def test_discovery_prefers_path_bash_and_rejects_unusable_launcher(tmp_path, monkeypatch):
    git = tmp_path / 'cmd/git.exe'
    git.parent.mkdir()
    git.touch()
    path_bash = tmp_path / 'path-bash.exe'
    path_bash.touch()
    fallback = tmp_path / 'usr/bin/bash.exe'
    fallback.parent.mkdir(parents=True)
    fallback.touch()
    monkeypatch.setattr(shutil, 'which', lambda name: str(path_bash))
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, b'GNU bash fixture', b''))
    assert discover_bash(git, windows=True) == str(path_bash)
    monkeypatch.setattr(subprocess, 'run', lambda args, **kwargs:
                        subprocess.CompletedProcess(args, 0,
                                                    b'GNU bash (x86_64-pc-linux-gnu)'
                                                    if args[0] == str(path_bash)
                                                    else b'GNU bash fixture', b''))
    assert discover_bash(git, windows=True) == str(fallback)


@pytest.mark.parametrize('path', ['spec/fixture.md', 'decisions/fixture.md', 'ordinary.txt'])
@pytest.mark.parametrize('authority', [None, '0', '1', 'true'])
@pytest.mark.parametrize('docs_fail', [False, True])
def test_authority_exception_never_skips_docs(hook_repo, path, authority, docs_fail):
    repo, git, bash = hook_repo
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('fixture\n', encoding='utf-8')
    subprocess.run([git, '-C', str(repo), 'add', '--', path], check=True)
    if docs_fail:
        (repo / 'docs-fail').touch()
    env = os.environ.copy()
    env.pop('NYX_AUTHORITY_COMMIT', None)
    if authority is not None:
        env['NYX_AUTHORITY_COMMIT'] = authority
    result = subprocess.run([bash, '.githooks/pre-commit'], cwd=repo, env=env,
                            capture_output=True, text=True)
    protected = path.startswith(('spec/', 'decisions/'))
    blocked = protected and authority != '1'
    assert (repo / 'checked').read_text() == 'checked', result.stderr
    assert result.returncode == int(blocked or docs_fail), result.stderr
    assert ('protected staged file' in result.stderr) == blocked
