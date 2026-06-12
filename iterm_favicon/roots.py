from pathlib import Path


def find_project_root(cwd):
    """Loop omhoog tot de eerste map met .git; anders de cwd zelf."""
    start = Path(cwd).resolve()
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start
