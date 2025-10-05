#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
python3 "${SCRIPT_DIR}/api_indexer.py" --src "${ROOT_DIR}/src/main/java" --res "${ROOT_DIR}/src/main/resources" --out "${ROOT_DIR}/inventory"
