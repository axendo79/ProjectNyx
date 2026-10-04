"""Exercise the tracked hook in disposable repositories, never this index."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hook_repo(tmp_path):
    git = shutil.which('git')
    assert git is not None, 'Git is required to exercise the pre-commit hook'
    if os.name == 'nt':
        bash = Path(git).resolve().parents[1] / 'bin/bash.exe'
    else:
        bash = shutil.which('bash')
    assert bash and Path(bash).is_file(), 'Git Bash is required for the tracked hook'
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
