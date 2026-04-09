#!/usr/bin/env bash
set -euo pipefail

MONGO_CONTAINER="${MONGO_CONTAINER:-stock_portal_mongo}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASS="${MONGO_PASS:-admin123}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"
TARGET_DB="${TARGET_DB:-stock_analysis}"

# Optional login smoke against backend API
REQUIRE_LOGIN_SMOKE="${REQUIRE_LOGIN_SMOKE:-false}"
LOGIN_URL="${LOGIN_URL:-http://localhost:8000/api/token}"
LOGIN_USER="${LOGIN_USER:-admin}"
LOGIN_PASS="${LOGIN_PASS:-admin123}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found" >&2
  exit 1
fi

if ! docker container inspect "$MONGO_CONTAINER" >/dev/null 2>&1; then
  echo "ERROR: mongo container not found: $MONGO_CONTAINER" >&2
  exit 1
fi

JSON_OUT="$(docker exec "$MONGO_CONTAINER" mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" --eval "const d=db.getSiblingDB('$TARGET_DB'); const required=['users','user_settings','system_config','ibkr_holdings','ibkr_nav_history','ibkr_trades','stock_data']; const out={}; required.forEach(c=>{out[c]=d.getCollection(c).countDocuments({});}); print(JSON.stringify(out));")"

if [[ -z "$JSON_OUT" ]]; then
  echo "ERROR: empty response from Mongo smoke query" >&2
  exit 1
fi

python3 - <<'PY' "$JSON_OUT"
import json, sys
payload = json.loads(sys.argv[1])
required = ["users", "user_settings", "system_config", "ibkr_holdings", "ibkr_nav_history", "ibkr_trades", "stock_data"]
missing = [k for k in required if k not in payload]
if missing:
    print(f"ERROR: missing required collections in smoke output: {missing}", file=sys.stderr)
    sys.exit(1)
zero_bad = [k for k in required if int(payload.get(k, 0)) <= 0]
if zero_bad:
    print(f"ERROR: required collections have zero counts: {zero_bad}", file=sys.stderr)
    print(json.dumps(payload, indent=2))
    sys.exit(2)
print("Smoke counts OK:")
print(json.dumps(payload, indent=2))
PY

if [[ "$REQUIRE_LOGIN_SMOKE" == "true" ]]; then
  echo "Running login smoke check: $LOGIN_URL"
  code=$(curl -sS -o /tmp/mongo_restore_login_smoke.json -w "%{http_code}" \
    -X POST "$LOGIN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "username=${LOGIN_USER}&password=${LOGIN_PASS}")
  if [[ "$code" != "200" ]]; then
    echo "ERROR: login smoke failed with HTTP $code" >&2
    cat /tmp/mongo_restore_login_smoke.json >&2 || true
    exit 3
  fi
  echo "Login smoke OK (HTTP 200)"
fi

echo "Mongo restore smoke check passed."
