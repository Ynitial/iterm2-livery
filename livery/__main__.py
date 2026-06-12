import argparse
import sys

from livery import app


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cwd", default=".")
    common.add_argument("--profiles-dir", default=str(app.DEFAULT_PROFILES))
    common.add_argument("--store-dir", default=str(app.DEFAULT_STORE))

    parser = argparse.ArgumentParser(prog="livery", parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("emit", parents=[common])
    sub.add_parser("reeval", parents=[common])
    p_set = sub.add_parser("set-icon", parents=[common])
    p_set.add_argument("path")
    p_ren = sub.add_parser("rename", parents=[common])
    p_ren.add_argument("custom", nargs="?", default="")
    sub.add_parser("clean", parents=[common])

    a = parser.parse_args(argv)
    dirs = {"profiles_dir": a.profiles_dir, "store_dir": a.store_dir}

    if a.cmd == "emit":
        sys.stdout.write(app.cmd_emit(cwd=a.cwd, **dirs))
    elif a.cmd == "reeval":
        sys.stdout.write(app.cmd_reeval(cwd=a.cwd, **dirs))
    elif a.cmd == "set-icon":
        sys.stdout.write(app.cmd_set_icon(a.path, cwd=a.cwd, **dirs))
    elif a.cmd == "rename":
        sys.stdout.write(app.cmd_rename(a.custom, cwd=a.cwd, **dirs))
    elif a.cmd == "clean":
        for root in app.cmd_clean(**dirs):
            sys.stderr.write(f"removed {root}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
