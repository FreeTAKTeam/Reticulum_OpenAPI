#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e '.[dev]'

pytest tests/test_example_emergency_management.py tests/examples/emergency_management tests/test_integration_webui_persistence.py

pushd examples/EmergencyManagement/webui > /dev/null
npm ci
npm run test -- --run --reporter=dot
popd > /dev/null
