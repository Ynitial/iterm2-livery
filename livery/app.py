import os
import time
from pathlib import Path

from livery import escapes, store
from livery.color import color_from_png
from livery.manifest import find_manifest, first_png
from livery.profile import (
    build_profile, default_inherited_settings, profile_file, profile_name, write_profile,
)
from livery.roots import find_project_root
from livery.tint import detect_theme, mute
from livery.title import root_name

DEFAULT_STORE = Path.home() / ".config" / "livery" / "dirs"
DEFAULT_SESSIONS = Path.home() / ".config" / "livery" / "sessions"
DEFAULT_PROFILES = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"


def _tab_strength():
    # 1.0 = volle merkkleur op de tab; lager blendt richting het thema.
    return float(os.environ.get("LIVERY_TAB_STRENGTH", "1.0"))


def _maxdepth():
    return int(os.environ.get("LIVERY_MAXDEPTH", "6"))


def _profile_delay():
    # Korte pauze ná het schrijven van een nieuw profiel, zodat iTerm2 het inlaadt
    # vóór de SetProfile-switch (anders mist het icoon bij het eerste bezoek).
    return float(os.environ.get("LIVERY_PROFILE_DELAY", "0.3"))


def _detect(root, force=False):
    """Bouw store-velden voor een root. None als 't geen project is (en niet force)."""
    manifest = find_manifest(root, maxdepth=_maxdepth())
    has_env = (Path(root) / ".env").exists()
    if manifest is None and not has_env and not force:
        return None
    png = first_png(manifest) if manifest else None
    if png is not None and not Path(png).exists():
        png = None
    rgb = color_from_png(png) if png else None
    source = "manifest" if png else ("env" if has_env else "name")
    return {
        "root": str(root),
        "icon_path": str(png) if png else None,
        "dominant_color": list(rgb) if rgb else None,
        "name": root_name(root),  # mapnaam; ook de profielnaam
        "source": source,
        "last_theme": None,
    }


def _ensure_profile(profiles_dir, entry, theme):
    """Schrijf het Dynamic Profile, maar alleen als de entry een icoon heeft."""
    if not entry.get("icon_path") or not entry.get("dominant_color"):
        return
    rgb = tuple(entry["dominant_color"])
    tab = mute(rgb, theme, _tab_strength())
    colors = default_inherited_settings()
    write_profile(profiles_dir, build_profile(entry["root"], entry["icon_path"], tab, colors))
    time.sleep(_profile_delay())  # geef iTerm2 tijd om het profiel in te laden


def _emit(entry, theme, custom=None):
    """Escape-output: eerst de profiel-switch/kleur, dán de sessienaam (titel).

    De profielnaam (= mapnaam) toont iTerm via de "Profile Name"-component; de
    sessienaam die wij hier zetten is de per-tab `rename` (Session Name-component).
    Titel als laatste, want SetProfile reset de sessienaam.
    """
    if entry.get("icon_path") and entry.get("dominant_color"):
        rgb = tuple(entry["dominant_color"])
        out = escapes.set_profile(profile_name(entry["root"]))
        out += escapes.tab_color(mute(rgb, theme, _tab_strength()))
    else:
        out = escapes.default_look()
    out += escapes.title(custom or entry["name"])
    return out


def _bare(root):
    """Niet-project-map: titel wissen (iTerm valt terug op z'n default) + default-look."""
    return escapes.reset()


def cmd_emit(cwd, profiles_dir, store_dir, session_dir=DEFAULT_SESSIONS, session_id=None):
    root = find_project_root(cwd)
    theme = detect_theme()
    custom = store.read_custom(session_dir, session_id)
    entry = store.read_entry(store_dir, root)

    if entry is None:
        entry = _detect(root)
        if entry is None:
            return _bare(root)
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
        _ensure_profile(profiles_dir, entry, theme)
        return _emit(entry, theme, custom)

    if entry.get("icon_path") and not Path(entry["icon_path"]).exists():
        return _bare(root)

    needs_profile = entry.get("icon_path") and not profile_file(profiles_dir, root).exists()
    if entry.get("last_theme") != theme or needs_profile:
        _ensure_profile(profiles_dir, entry, theme)
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
    return _emit(entry, theme, custom)


def cmd_scan(cwd, profiles_dir, store_dir, session_dir=DEFAULT_SESSIONS, session_id=None):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = _detect(root)
    if entry is None:
        return _bare(root)
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme, store.read_custom(session_dir, session_id))


def cmd_set_icon(icon_path, cwd, profiles_dir, store_dir, session_dir=DEFAULT_SESSIONS, session_id=None):
    root = find_project_root(cwd)
    theme = detect_theme()
    icon = Path(icon_path).expanduser().resolve()
    rgb = color_from_png(icon)
    if rgb is None:
        return escapes.reset()
    entry = {
        "root": str(root), "icon_path": str(icon), "dominant_color": list(rgb),
        "name": root_name(root), "source": "manual", "last_theme": theme,
    }
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme, store.read_custom(session_dir, session_id))


def cmd_rename(custom, cwd, profiles_dir, store_dir, session_dir=DEFAULT_SESSIONS, session_id=None):
    root = find_project_root(cwd)
    theme = detect_theme()
    custom = custom or None
    store.write_custom(session_dir, session_id, custom)  # per tab, gekoppeld aan session_id
    entry = store.read_entry(store_dir, root) or _detect(root, force=True)
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme, custom)


def cmd_clean(profiles_dir, store_dir):
    removed = []
    for entry in list(store.iter_entries(store_dir)):
        root = entry.get("root", "")
        if root and not Path(root).exists():
            store.delete_entry(store_dir, root)
            pf = profile_file(profiles_dir, root)
            if pf.exists():
                pf.unlink()
            removed.append(root)
    return removed
