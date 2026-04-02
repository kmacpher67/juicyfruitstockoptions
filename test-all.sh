#!/usr/bin/env bash

set -euo pipefail

echo "Running all tests..."

if ! command -v pytest >/dev/null 2>&1; then
  echo "Error: pytest is not installed or not on PATH."
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Error: node is not installed or not on PATH."
  exit 1
fi

echo "Backend tests..."
pytest

echo "Frontend tests..."
mapfile -d '' frontend_tests < <(
  find frontend/src -type f \( \
    -name "*.test.js" -o -name "*.spec.js" -o \
    -name "*.test.jsx" -o -name "*.spec.jsx" -o \
    -name "*.test.ts" -o -name "*.spec.ts" -o \
    -name "*.test.tsx" -o -name "*.spec.tsx" \
  \) -print0
)

if ((${#frontend_tests[@]} == 0)); then
  echo "No frontend test files found under frontend/src."
else
  node --test "${frontend_tests[@]}"
fi

echo "All tests completed."
