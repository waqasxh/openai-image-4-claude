#!/usr/bin/env bash
# Pre-flight check for the OpenAI Image Gen plugin: API key, uv, main.py.
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$(dirname "${SCRIPT_DIR}")}"
HOME_ENV="${HOME}/.config/openai-image-4-claude/.env"
ok=true

is_real() { [[ -n "$1" && "$1" != "your_api_key_here" && "$1" != "your_key_here" ]]; }

env_file_has_key() {
  [[ -f "$1" ]] || return 1
  local v
  v="$(grep -m1 '^OPENAI_API_KEY=' "$1" | cut -d= -f2- | tr -d '\r"'"'" || true)"
  is_real "${v}"
}

echo "=== OpenAI Image Gen Environment Check ==="
if is_real "${OPENAI_API_KEY:-}"; then
  echo "[OK] OPENAI_API_KEY set in environment"
elif env_file_has_key "${HOME_ENV}" || env_file_has_key "${PLUGIN_DIR}/.env"; then
  echo "[OK] OPENAI_API_KEY found in .env"
else
  echo "[ERROR] OPENAI_API_KEY not found"
  echo "        Create ~/.config/openai-image-4-claude/.env with OPENAI_API_KEY=your_key"
  echo "        Key: https://platform.openai.com/api-keys (needs billing credit)"
  ok=false
fi

if command -v uv >/dev/null 2>&1; then echo "[OK] uv installed"; else
  echo "[ERROR] uv not found (https://astral.sh/uv)"; ok=false; fi

if [[ -f "${PLUGIN_DIR}/main.py" ]]; then echo "[OK] main.py found"; else
  echo "[ERROR] main.py missing in ${PLUGIN_DIR}"; ok=false; fi

[[ "${ok}" == true ]] && { echo "=== All checks passed ==="; exit 0; }
echo "=== Environment check failed ==="; exit 2
