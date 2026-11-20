# Macquarium prompt for bash. Sourced from ~/.bash_profile; only active after `macquarium on`.
MQ_HOME="${MACQUARIUM_HOME:-$HOME/.macquarium}"
if [ -f "$MQ_HOME/state/enabled" ]; then
  _mq_fish=( "><>" "><(((\`>" ">-{{'>" "><=>" "<><" )
  _mq_colors=( 208 214 203 81 141 226 213 )
  _mq_prompt() {
    local st=$? f c branch=""
    f="${_mq_fish[$((RANDOM % ${#_mq_fish[@]}))]}"
    c="${_mq_colors[$((RANDOM % ${#_mq_colors[@]}))]}"
    branch="$(git symbolic-ref --short HEAD 2>/dev/null)"
    [ -n "$branch" ] && branch=" \[\e[38;5;179m\]⚓ $branch"
    local arrow=45; [ $st -ne 0 ] && arrow=203
    PS1="\[\e[38;5;24m\]≋\[\e[38;5;31m\]≋\[\e[38;5;38m\]≋ \[\e[38;5;159m\]\w$branch \[\e[38;5;${c}m\]$f\[\e[0m\]\n\[\e[38;5;${arrow}m\]o ›\[\e[0m\] "
  }
  [ "${MACQUARIUM_PROMPT:-0}" = "1" ] && PROMPT_COMMAND="_mq_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
  case $- in *i*)
    if [ -z "$MACQUARIUM_ASKED" ] && [ "$TERM_PROGRAM" = "Apple_Terminal" ] && [ -z "$SSH_CONNECTION" ] && [ ! -f "$MQ_HOME/state/no_ask" ]; then
      export MACQUARIUM_ASKED=1
      printf 'Take care of the aquarium? (y/n) '
      read -r -n 1 _mq_ans; echo
      case "$_mq_ans" in y|Y) command macquarium care ;; esac
      unset _mq_ans
    fi ;;
  esac
fi
