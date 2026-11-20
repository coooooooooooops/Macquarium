# Macquarium prompt for zsh. Sourced from ~/.zshrc; only active after `macquarium on`.
MQ_HOME="${MACQUARIUM_HOME:-$HOME/.macquarium}"
[[ -f "$MQ_HOME/state/enabled" ]] || return 0

# The underwater prompt is opt-in: export MACQUARIUM_PROMPT=1 before this line to use it.
if [[ "${MACQUARIUM_PROMPT:-0}" == "1" ]]; then
  autoload -Uz vcs_info add-zsh-hook
  setopt PROMPT_SUBST
  zstyle ':vcs_info:git:*' formats ' %F{179}⚓ %b%f'
  zstyle ':vcs_info:*' enable git

  _mq_fish=( "><>" "><(((\`>" ">-{{'>" "><=>" "<><" )
  _mq_colors=( 208 214 203 81 141 226 213 )

  _mq_precmd() {
    vcs_info
    _mq_f="${_mq_fish[$(( RANDOM % ${#_mq_fish} + 1 ))]}"
    _mq_c="${_mq_colors[$(( RANDOM % ${#_mq_colors} + 1 ))]}"
    # "depth" = how many folders down you are
    local p="${PWD#$HOME}"; p="${p#/}"
    if [[ -z "$p" ]]; then _mq_depth=0; else _mq_depth=${#${(s:/:)p}}; fi
  }
  add-zsh-hook precmd _mq_precmd

  PROMPT=$'%F{24}≋%F{31}≋%F{38}≋%f %F{159}%~%f${vcs_info_msg_0_} %F{${_mq_c}}${_mq_f}%f\n%(?.%F{45}.%F{203})o ›%f '
  RPROMPT='%F{24}↓ ${_mq_depth}m%f'
fi

_mq_startup() {
  [[ -o interactive ]] || return 0
  [[ -n "$MACQUARIUM_ASKED" ]] && return 0        # only the first shell in a window, not subshells
  export MACQUARIUM_ASKED=1
  local facts=(
    "Octopuses have three hearts."
    "A group of jellyfish is called a smack."
    "Clownfish are born male; the dominant fish in a group can become female."
    "Male seahorses carry and give birth to the young."
    "Sharks have been around longer than trees."
    "Much of the white sand on coral reefs comes from parrotfish."
    "Sea stars have no blood; they pump seawater through their bodies."
    "Dolphins rest one half of their brain at a time."
    "Cleaner wrasse run 'cleaning stations' where bigger fish queue up."
    "Blacktip reef sharks are shy and usually avoid people."
  )
  if [[ "${MACQUARIUM_GREETING:-0}" == "1" ]]; then
    print "Fish fact: ${facts[$(( RANDOM % ${#facts} + 1 ))]}"
  fi
  [[ "$TERM_PROGRAM" == "Apple_Terminal" && -z "$SSH_CONNECTION" && ! -f "$MQ_HOME/state/no_ask" ]] || return 0
  local full="" mood=""
  [[ -f "$MQ_HOME/state/tank.json" ]] && full=$(sed -n 's/.*"full": *\([0-9]*\).*/\1/p' "$MQ_HOME/state/tank.json")
  if [[ -n "$full" ]]; then
    if (( full < 35 )); then mood=" (the fish are hungry)"
    elif (( full < 65 )); then mood=" (fullness ${full}%%)"
    else mood=" (the fish are happy)"; fi
  fi
  if read -q "?$(print -P "Take care of the aquarium?${mood} (y/n) ")"; then
    print; command macquarium care
  else
    print
  fi
}
_mq_startup
