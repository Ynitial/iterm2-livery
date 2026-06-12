import os
from pathlib import Path

from livery import escapes, store
from livery.color import color_from_png
from livery.manifest import find_manifest, first_png
from livery.profile import build_profile, profile_file, profile_name, write_profile
from livery.roots import find_project_root
from livery.tint import detect_theme, mute
from livery.title import base_name, tab_title

DEFAULT_STORE = Path.home() / ".config" / "livery" / "dirs"
DEFAULT_PROFILES = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"


def _tab_strength():
    return float(os.environ.get("LIVERY_TAB_STRENGTH", "0.15"))


def _bg_strength():
    return float(os.environ.get("LIVERY_BG_STRENGTH", "0.07"))


def _maxdepth():
    return int(os.environ.get("LIVERY_MAXDEPTH", "6"))


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
        "name": base_name(root, manifest),
        "custom_name": None,
        "source": source,
        "last_theme": None,
    }


def _ensure_profile(profiles_dir, entry, theme):
    """Schrijf het Dynamic Profile, maar alleen als de entry een icoon heeft."""
    if not entry.get("icon_path") or not entry.get("dominant_color"):
        return
    rgb = tuple(entry["dominant_color"])
    tab = mute(rgb, theme, _tab_strength())
    bg = mute(rgb, theme, _bg_strength())
    write_profile(profiles_dir, build_profile(entry["root"], entry["icon_path"], tab, bg))


def _emit(entry, theme):
    """Escape-output: titel + (icoon-profiel + kleur) OF default-look."""
    out = escapes.title(tab_title(entry["name"], entry.get("custom_name")))
    if entry.get("icon_path") and entry.get("dominant_color"):
        rgb = tuple(entry["dominant_color"])
        out += escapes.set_profile(profile_name(entry["root"]))
        out += escapes.tab_color(mute(rgb, theme, _tab_strength()))
    else:
        out += escapes.default_look()
    return out


def cmd_emit(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = store.read_entry(store_dir, root)

    if entry is None:
        entry = _detect(root)
        if entry is None:
            return escapes.reset()
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
        _ensure_profile(profiles_dir, entry, theme)
        return _emit(entry, theme)

    if entry.get("icon_path") and not Path(entry["icon_path"]).exists():
        return escapes.reset()

    needs_profile = entry.get("icon_path") and not profile_file(profiles_dir, root).exists()
    if entry.get("last_theme") != theme or needs_profile:
        _ensure_profile(profiles_dir, entry, theme)
        entry["last_theme"] = theme
        store.write_entry(store_dir, root, entry)
    return _emit(entry, theme)


def cmd_reeval(cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    old = store.read_entry(store_dir, root)
    entry = _detect(root)
    if entry is None:
        return escapes.reset()
    if old and old.get("custom_name"):
        entry["custom_name"] = old["custom_name"]
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


def cmd_set_icon(icon_path, cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    icon = Path(icon_path).expanduser().resolve()
    rgb = color_from_png(icon)
    if rgb is None:
        return escapes.reset()
    old = store.read_entry(store_dir, root)
    name = old["name"] if old and old.get("name") else base_name(root, find_manifest(root, maxdepth=_maxdepth()))
    entry = {
        "root": str(root), "icon_path": str(icon), "dominant_color": list(rgb),
        "name": name, "custom_name": old.get("custom_name") if old else None,
        "source": "manual", "last_theme": theme,
    }
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


def cmd_rename(custom, cwd, profiles_dir, store_dir):
    root = find_project_root(cwd)
    theme = detect_theme()
    entry = store.read_entry(store_dir, root) or _detect(root, force=True)
    entry["custom_name"] = custom or None
    entry["last_theme"] = theme
    store.write_entry(store_dir, root, entry)
    _ensure_profile(profiles_dir, entry, theme)
    return _emit(entry, theme)


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
