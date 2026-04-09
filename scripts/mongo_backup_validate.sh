#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${1:-}"

if [[ -z "$ARTIFACT_DIR" ]]; then
  echo "Usage: $0 <artifact_dir>" >&2
  exit 1
fi

if [[ ! -d "$ARTIFACT_DIR" ]]; then
  echo "ERROR: Artifact directory not found: $ARTIFACT_DIR" >&2
  exit 1
fi

REQUIRED=("mongo_dump" "manifest.json" "sha256sums.txt")
for item in "${REQUIRED[@]}"; do
  if [[ ! -e "$ARTIFACT_DIR/$item" ]]; then
    echo "ERROR: Missing required artifact item: $item" >&2
    exit 1
  fi
done

if [[ ! -d "$ARTIFACT_DIR/mongo_dump" ]]; then
  echo "ERROR: mongo_dump is not a directory" >&2
  exit 1
fi

if ! python -m json.tool "$ARTIFACT_DIR/manifest.json" >/dev/null 2>&1; then
  echo "ERROR: manifest.json is not valid JSON" >&2
  exit 1
fi

echo "[1/2] Required files and manifest are valid."
echo "[2/2] Verifying checksums..."
(
  cd "$ARTIFACT_DIR"
  sha256sum -c sha256sums.txt
)

echo "Validation OK: $ARTIFACT_DIR"
