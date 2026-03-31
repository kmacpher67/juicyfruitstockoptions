#!/usr/bin/env bash
# ibkr-ibapi-update.sh
#
# Downloads the latest IBKR TWS API source and installs the Python client
# into vendor/ibapi/ so requirements.txt can reference it as a local path.
#
# Usage:
#   ./ibkr-ibapi-update.sh              # auto-detect latest from IBKR CDN
#   ./ibkr-ibapi-update.sh 10.26.01     # pin a specific version
#
# After running, rebuild your Docker image:
#   docker-compose up --build
#
# Notes:
#   - IBKR does not publish new ibapi versions to PyPI. The PyPI package is
#     frozen at 9.81.1.post1 (circa 2020). All newer versions must be
#     installed from the IBKR TWS API source zip directly.
#   - The zip contains IBJts/source/pythonclient/ — that directory IS the
#     installable Python package (has setup.py + ibapi/ module).
#   - IBKR CDN URL pattern:
#       https://interactivebrokers.github.io/downloads/twsapi_macunix.{VERSION}.zip

set -euo pipefail

VENDOR_DIR="$(cd "$(dirname "$0")" && pwd)/vendor/ibapi"
TMP_DIR="$(mktemp -d)"
IBKR_CDN_BASE="https://interactivebrokers.github.io/downloads"

# --- version resolution ---
if [[ $# -ge 1 ]]; then
    VERSION="$1"
    echo "[ibkr-ibapi-update] Using pinned version: $VERSION"
else
    # Attempt to scrape the IBKR downloads page for the latest macunix zip version.
    # Falls back to a known-good default if scraping fails.
    FALLBACK_VERSION="10.26.01"
    echo "[ibkr-ibapi-update] Detecting latest version from IBKR CDN..."
    DETECTED=$(curl -sL --max-time 15 "https://interactivebrokers.github.io/" \
        | grep -oP 'twsapi_macunix\.\K[0-9]+\.[0-9]+' \
        | sort -V | tail -1 || true)
    if [[ -n "$DETECTED" ]]; then
        VERSION="$DETECTED"
        echo "[ibkr-ibapi-update] Detected version: $VERSION"
    else
        VERSION="$FALLBACK_VERSION"
        echo "[ibkr-ibapi-update] Could not detect version, using fallback: $VERSION"
    fi
fi

ZIP_NAME="twsapi_macunix.${VERSION}.zip"
DOWNLOAD_URL="${IBKR_CDN_BASE}/${ZIP_NAME}"
ZIP_PATH="${TMP_DIR}/${ZIP_NAME}"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# --- download ---
echo "[ibkr-ibapi-update] Downloading: $DOWNLOAD_URL"
if ! curl -fL --max-time 120 -o "$ZIP_PATH" "$DOWNLOAD_URL"; then
    echo ""
    echo "ERROR: Download failed."
    echo "  URL tried: $DOWNLOAD_URL"
    echo ""
    echo "Manual steps:"
    echo "  1. Go to: https://www.interactivebrokers.com/en/trading/ib-api.php"
    echo "  2. Download the Linux/Mac version zip"
    echo "  3. Re-run:  ./ibkr-ibapi-update.sh <version>"
    echo "     e.g.     ./ibkr-ibapi-update.sh 10.26.01"
    exit 1
fi

# --- extract pythonclient only ---
echo "[ibkr-ibapi-update] Extracting pythonclient from zip..."
unzip -q "$ZIP_PATH" "IBJts/source/pythonclient/*" -d "$TMP_DIR"

PYTHONCLIENT_SRC="${TMP_DIR}/IBJts/source/pythonclient"
if [[ ! -d "$PYTHONCLIENT_SRC" ]]; then
    echo "ERROR: Expected path not found in zip: IBJts/source/pythonclient/"
    echo "The zip structure may have changed. Inspect: $ZIP_NAME"
    exit 1
fi

# --- install into vendor/ ---
echo "[ibkr-ibapi-update] Installing into ${VENDOR_DIR}..."
rm -rf "$VENDOR_DIR"
mkdir -p "$(dirname "$VENDOR_DIR")"
cp -r "$PYTHONCLIENT_SRC" "$VENDOR_DIR"

# Sanity check: setup.py must be present for pip to install from local path
if [[ ! -f "${VENDOR_DIR}/setup.py" ]]; then
    echo "WARNING: setup.py not found in ${VENDOR_DIR}. pip install may fail."
    echo "Check the extracted contents:"
    ls "$VENDOR_DIR"
fi

echo ""
echo "[ibkr-ibapi-update] Done."
echo "  Installed IBKR TWS API ${VERSION} -> ${VENDOR_DIR}"
echo ""
echo "Next steps:"
echo "  1. Verify:  pip install -e ./vendor/ibapi   (local dev)"
echo "  2. Rebuild: docker-compose up --build"
