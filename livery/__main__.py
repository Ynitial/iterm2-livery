import argparse
import sys

from livery import app


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cwd", default=".")
    common.add_argument("--profiles-dir", default=str(app.DEFAULT_PROFILES))
    common.add_argument("--store-dir", default=str(app.DEFAULT_STORE))
    common.add_argument("--session-dir", default=str(app.DEFAULT_SESSIONS))
    common.add_argument("--session", default="")  # $ITERM_SESSION_ID (per tab)

    parser = argparse.ArgumentParser(prog="livery", parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("emit", parents=[common])
    sub.add_parser("scan", parents=[common])
    p_set = sub.add_parser("icon", parents=[common])
    p_set.add_argument("path")
    p_ren = sub.add_parser("rename", parents=[common])
    p_ren.add_argument("name", nargs="?", default="")
    p_ren.add_argument("-p", "--project", action="store_true",
                       help="hernoem het hele project (profielnaam) i.p.v. deze tab")
    sub.add_parser("clean", parents=[common])
    p_cmd = sub.add_parser("command-start", parents=[common])
    p_cmd.add_argument("name")
    sub.add_parser("command-end", parents=[common])
    sub.add_parser("commands", parents=[common])
    sub.add_parser("claude-setup", parents=[common])

    a = parser.parse_args(argv)
    dirs = {"profiles_dir": a.profiles_dir, "store_dir": a.store_dir}
    sess = {"session_dir": a.session_dir, "session_id": a.session or None}

    if a.cmd == "emit":
        sys.stdout.write(app.cmd_emit(cwd=a.cwd, **dirs, **sess))
    elif a.cmd == "scan":
        sys.stdout.write(app.cmd_scan(cwd=a.cwd, **dirs, **sess))
    elif a.cmd == "icon":
        sys.stdout.write(app.cmd_set_icon(a.path, cwd=a.cwd, **dirs, **sess))
    elif a.cmd == "rename":
        sys.stdout.write(app.cmd_rename(a.name, cwd=a.cwd, project=a.project, **dirs, **sess))
    elif a.cmd == "clean":
        for root in app.cmd_clean(**dirs):
            sys.stderr.write(f"removed {root}\n")
    elif a.cmd == "command-start":
        sys.stdout.write(app.cmd_command_start(a.name))
    elif a.cmd == "command-end":
        sys.stdout.write(app.cmd_command_end())
    elif a.cmd == "commands":
        sys.stdout.write(app.cmd_commands())
    elif a.cmd == "claude-setup":
        sys.stdout.write(app.cmd_claude_setup())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
