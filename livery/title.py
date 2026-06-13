from pathlib import Path


def root_name(root):
    """De titel-basis: de mapnaam van de project-root."""
    return Path(root).name


def tab_title(base, custom=None):
    """'<base> | <custom>' als er een custom naam is, anders '<base>'."""
    return f"{base} | {custom}" if custom else base
