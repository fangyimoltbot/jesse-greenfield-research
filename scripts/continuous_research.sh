#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."

MAX_CYCLES=${MAX_CYCLES:-24}
MINUTES_PER_CYCLE=${MINUTES_PER_CYCLE:-20}
TARGET_NET=${TARGET_NET:-1.0}
TIMEFRAMES=${TIMEFRAMES:-"1h 4h 1D"}

mkdir -p reports

echo "[continuous] started $(date -u +%FT%TZ) cycles=$MAX_CYCLES minutes=$MINUTES_PER_CYCLE target_net=$TARGET_NET timeframes=$TIMEFRAMES"

read -r -a TF_ARR <<< "$TIMEFRAMES"
TF_COUNT=${#TF_ARR[@]}

for ((i=1;i<=MAX_CYCLES;i++)); do
  idx=$(( (i-1) % TF_COUNT ))
  tf=${TF_ARR[$idx]}
  echo "[continuous] cycle $i/$MAX_CYCLES timeframe=$tf"
  python3 scripts/nightly_research.py --minutes "$MINUTES_PER_CYCLE" --batches 45 --timeframe "$tf" || true

  latest_json=$(ls -1t reports/run_*.json | head -n1)
  best=$(python3 - <<PY
import json
p='$latest_json'
with open(p) as f:
    d=json.load(f)
vals=[r.get('net_profit_percentage',-999) for r in d.get('results',[]) if 'error' not in r]
print(max(vals) if vals else -999)
PY
)
  echo "[continuous] best net=${best}% from ${latest_json}"

  git add strategies scripts reports README.md .gitignore docker-compose.yml 2>/dev/null || true
  git commit -m "research: cycle $i best_net=${best}%" >/dev/null 2>&1 || true
  git push >/dev/null 2>&1 || true

  reached=$(python3 - <<PY
best=float('$best')
print('yes' if best >= float('$TARGET_NET') else 'no')
PY
)
  if [[ "$reached" == "yes" ]]; then
    echo "[continuous] target reached: ${best}% >= ${TARGET_NET}%"
    break
  fi

done

echo "[continuous] finished $(date -u +%FT%TZ)"
