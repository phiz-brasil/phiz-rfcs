#!/usr/bin/env bash
# PreToolUse hook (Bash): before `git push` and `gh pr create`, run the guardrail (tools/guardrail.py, docs/spec/v2/guardrail.md) and refuse when it fails.
# Every other command passes. GUARDRAIL_CMD replaces the checker (the tests use it).
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
if printf '%s' "$cmd" | grep -Eq '(^|[;&|(][ ]*)(git push|gh pr create)([ ]|$)'; then
  cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true
  out=$(bash -c "${GUARDRAIL_CMD:-python3 tools/guardrail.py --base origin/main}" 2>&1)
  if [ $? -ne 0 ]; then
    printf 'Guardrail refused this command (docs/spec/v2/guardrail.md):\n%s\n' "$out" >&2
    exit 2
  fi
fi
exit 0
