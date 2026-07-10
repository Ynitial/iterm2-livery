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

# --- commando-wrappers: tijdelijke "AI-look" per invocation (bv. `claude`) ---
# Voor elk commando in ~/.config/livery/commands.json definiëren we een functie
# die de look aanzet, het echte commando draait, en na afloop (ook bij Ctrl-C,
# via `always`) de normale look herstelt.
_livery_define_wrappers() {
  [[ "$TERM_PROGRAM" == "iTerm.app" ]] || return 0
  local name fs run env exec_cmd
  while IFS=$'\t' read -r name fs run; do
    [[ -n "$name" ]] || continue
    unalias "$name" 2>/dev/null   # bv. dev='npm run dev' mag de functie niet overschaduwen
    env=""
    [[ "$fs" == "1" ]] && env="CLAUDE_CODE_NO_FLICKER=1 "  # fullscreen (Task 8: verifieer)
    if [[ -n "$run" ]]; then exec_cmd="$run"; else exec_cmd="command $name"; fi
    eval "
    ${name}() {
      print -rn -- \"\$(_livery_py command-start ${name} --cwd \"\$PWD\" --session \"\$ITERM_SESSION_ID\" 2>/dev/null)\"
      {
        ${env}${exec_cmd} \"\$@\"
      } always {
        local rc=\$?
        _livery_run
        return \$rc
      }
    }
    "
  done < <(_livery_py commands 2>/dev/null)
}
_livery_define_wrappers

# `builtin` omzeilt een eventuele user-alias die `autoload` overschaduwt
# (bv. `alias autoload="composer dump"`) — anders faalt het laden van add-zsh-hook.
builtin autoload -Uz add-zsh-hook
add-zsh-hook chpwd _livery_run
_livery_run   # bij startup
