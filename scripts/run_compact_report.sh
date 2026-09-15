#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -n "${CODEX_BUNDLED_PYTHON:-}" ] && [ -x "$CODEX_BUNDLED_PYTHON" ]; then
  PYTHON_BIN=$CODEX_BUNDLED_PYTHON
else
  PYTHON_BIN=""
  for candidate in "$HOME"/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; do
    if [ -x "$candidate" ]; then
      PYTHON_BIN=$candidate
      break
    fi
  done
  if [ -z "$PYTHON_BIN" ] && command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import reportlab, pypdf, PIL' >/dev/null 2>&1; then
      PYTHON_BIN=$(command -v python3)
    fi
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "No usable Python runtime with reportlab, pypdf, and Pillow was found." >&2
  echo "In Codex, call load_workspace_dependencies and set CODEX_BUNDLED_PYTHON to its Python executable." >&2
  exit 2
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/compact_report.py" "$@"
