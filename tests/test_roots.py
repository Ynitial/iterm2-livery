from pathlib import Path

from livery.roots import find_project_root


def test_walks_up_to_git_dir(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "src" / "components"
    sub.mkdir(parents=True)
    assert find_project_root(sub) == tmp_path.resolve()


def test_falls_back_to_cwd_without_git(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_project_root(sub) == sub.resolve()
