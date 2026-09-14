#!/usr/bin/env bash
#
# About the claude code's status line - https://code.claude.com/docs/en/statusline
# Claude passes data in JSON forfmat to this sscript
# Available data is - https://code.claude.com/docs/en/statusline#available-data
#
# Claude Code status line - dir, vcs, user@host, model, effort, context %
input=$(cat)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "?"')
model=$(echo "$input" | jq -r '.model.display_name // "?"')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
used_tokens=$(echo "$input" | jq -r '((.context_window.total_input_tokens // 0) + (.context_window.total_output_tokens // 0))')
effort=$(echo "$input" | jq -r '.effort.level // empty')
home="$HOME"
short_cwd="${cwd/#$home/\~}"
git_branch=""
if git_out=$(GIT_OPTIONAL_LOCKS=0 git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null); then
  git_branch=" $git_out"
fi
user_host="$(whoami)@$(hostname -s)"
effort_info=""
if [ -n "$effort" ]; then
  case "$effort" in
    low)    glyph="▁" ;;
    medium) glyph="▂" ;;
    high)   glyph="▲" ;;
    xhigh)  glyph="⬆" ;;
    max)    glyph="★" ;;
    *)      glyph="?" ;;
  esac
  effort_info=" ${glyph}${effort}"
fi
ctx_info=""
if [ -n "$used_pct" ]; then
  ctx_pct=$(printf '%.0f' "$used_pct")
  if [ "$used_tokens" -ge 1000 ]; then
    ctx_tokens=$(awk -v t="$used_tokens" 'BEGIN { printf "%.1fK", t / 1000 }')
  else
    ctx_tokens="$used_tokens"
  fi
  ctx_info=" ctx:${ctx_tokens}(${ctx_pct}%)"
fi
printf "\033[34m%s\033[0m\033[32m%s\033[0m \033[90m%s\033[0m \033[33m%s\033[0m\033[35m%s\033[0m\033[36m%s\033[0m" \
  "$short_cwd" "$git_branch" "$user_host" "$model" "$effort_info" "$ctx_info"
