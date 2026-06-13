# livery — source dit vanuit ~/.zshrc
LIVERY_DIR="${0:A:h}"

_livery_py() {
  # Draai het pakket met de repo-root op PYTHONPATH zodat `import livery` werkt.
  PYTHONPATH="$LIVERY_DIR" python3 -m livery "$@"
}

_livery_run() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local logfile="/dev/null"
  [[ -n "$LIVERY_LOG" ]] && logfile="$HOME/.config/livery/log"
  local out
  out="$(_livery_py emit --cwd "$PWD" --session "$ITERM_SESSION_ID" 2>>"$logfile")" || return 0
  print -rn -- "$out"
}

livery() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || { echo "livery: alleen in iTerm2"; return 1; }
  local out
  case "$1" in
    scan)      out="$(_livery_py scan --cwd "$PWD" --session "$ITERM_SESSION_ID")" ;;
    icon)      out="$(_livery_py icon "$2" --cwd "$PWD" --session "$ITERM_SESSION_ID")" ;;
    rename|rn) out="$(_livery_py rename "${@:2}" --cwd "$PWD" --session "$ITERM_SESSION_ID")" ;;
    clean)     _livery_py clean; return 0 ;;
    *) echo "usage: livery {rename|rn [naam] [-p|--project]|icon <pad>|scan|clean}"; return 1 ;;
  esac
  print -rn -- "$out"
}

# `builtin` omzeilt een eventuele user-alias die `autoload` overschaduwt
# (bv. `alias autoload="composer dump"`) — anders faalt het laden van add-zsh-hook.
builtin autoload -Uz add-zsh-hook
add-zsh-hook chpwd _livery_run
_livery_run   # bij startup
