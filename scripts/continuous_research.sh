#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

MAX_CYCLES=${MAX_CYCLES:-24}
MINUTES_PER_CYCLE=${MINUTES_PER_CYCLE:-20}
TARGET_NET=${TARGET_NET:-1.0}

mkdir -p reports

echo "[continuous] started $(date -u +%FT%TZ) cycles=$MAX_CYCLES minutes=$MINUTES_PER_CYCLE target_net=$TARGET_NET"

for ((i=1;i<=MAX_CYCLES;i++)); do
  echo "[continuous] cycle $i/$MAX_CYCLES"
  python3 scripts/nightly_research.py --minutes "$MINUTES_PER_CYCLE" --batches 45

  latest_json=$(ls -1t reports/run_*.json | head -n1)
  best=$(python3 - <<PY
import json
p='$latest_json'
with open(p) as f:
    d=json.load(f)
vals=[r.get('net_profit_percentage',-999) for r in d['results'] if 'error' not in r]
print(max(vals) if vals else -999)
PY
)
  echo "[continuous] best net=${best}% from ${latest_json}"

  git add strategies scripts reports README.md .gitignore docker-compose.yml 2>/dev/null || true
  git commit -m "research: cycle $i best_net=${best}%" >/dev/null 2>&1 || true
  git push >/dev/null 2>&1 || true

  python3 - <<PY
best=float('$best')
import sys
sys.exit(0 if best >= float('$TARGET_NET') else 1)
PY
  if [[ $? -eq 0 ]]; then
    echo "[continuous] target reached: ${best}% >= ${TARGET_NET}%"
    break
  fi

done

echo "[continuous] finished $(date -u +%FT%TZ)"
