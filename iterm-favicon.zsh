# iterm-favicon — source dit vanuit ~/.zshrc
ITERM_FAVICON_DIR="${0:A:h}"

_iterm_favicon_py() {
  # Draai het pakket met de repo-root op PYTHONPATH zodat `import iterm_favicon` werkt.
  PYTHONPATH="$ITERM_FAVICON_DIR" python3 -m iterm_favicon "$@"
}

_iterm_favicon_run() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local logfile="/dev/null"
  [[ -n "$ITERM_FAVICON_LOG" ]] && logfile="$HOME/.config/iterm-favicon/log"
  local out
  out="$(_iterm_favicon_py emit --cwd "$PWD" 2>>"$logfile")" || return 0
  print -rn -- "$out"
}

iterm-favicon() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || { echo "iterm-favicon: alleen in iTerm2"; return 1; }
  local out
  case "$1" in
    reeval)   out="$(_iterm_favicon_py reeval --cwd "$PWD")" ;;
    set-icon) out="$(_iterm_favicon_py set-icon "$2" --cwd "$PWD")" ;;
    rename)   out="$(_iterm_favicon_py rename "$2" --cwd "$PWD")" ;;
    clean)    _iterm_favicon_py clean; return 0 ;;
    *) echo "usage: iterm-favicon {reeval|set-icon <pad>|rename [naam]|clean}"; return 1 ;;
  esac
  print -rn -- "$out"
}

autoload -U add-zsh-hook
add-zsh-hook chpwd _iterm_favicon_run
_iterm_favicon_run   # bij startup
