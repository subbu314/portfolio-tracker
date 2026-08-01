#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
DL="${DOWNLOADS_DIR:-$HOME/Downloads}"

# Console: ≤365 days / typically one Indian FY per file; EQ and MF separate.
# Multi-file one-shot via repeated multipart field name `files`.
EQUITY_CSVS=(
  "${DL}/tradebook-RYY010-EQ (2).csv"
  "${DL}/tradebook-RYY010-EQ (1).csv"
  "${DL}/tradebook-RYY010-EQ.csv"
)
# MF (3) omitted — duplicate of MF (2)
MF_CSVS=(
  "${DL}/tradebook-RYY010-MF.csv"
  "${DL}/tradebook-RYY010-MF (1).csv"
  "${DL}/tradebook-RYY010-MF (2).csv"
)

echo "== health =="
curl -sf "$BASE/health" | tee /tmp/pt-health.json
grep -q '"status":"ok"' /tmp/pt-health.json

echo "== auth status (pre) =="
curl -sf "$BASE/auth/status" | tee /tmp/pt-auth-status.json

FORM_ARGS=()
for f in "${EQUITY_CSVS[@]}" "${MF_CSVS[@]}"; do
  test -f "$f" || { echo "MISSING: $f"; exit 1; }
  FORM_ARGS+=(-F "files=@${f};type=text/csv")
done

echo "== multi-file import (EQ + MF FY slices) =="
curl -sf -X POST "$BASE/import/csv" "${FORM_ARGS[@]}" | tee /tmp/pt-import-batch.json
# Fail smoke if any file rejected (wrong input)
python3 - <<'PY'
import json, sys
body = json.load(open("/tmp/pt-import-batch.json"))
assert "summary" in body, body
if body["summary"]["rejected"]:
    for row in body["files"]:
        if not row.get("ok", True):
            print("REJECTED", row.get("filename"), row.get("code"), row.get("action", "")[:80])
    sys.exit(1)
print("accepted", body["summary"]["accepted"], "new", body["summary"]["new"])
for row in body["files"]:
    print(row["filename"], row.get("financial_years"), "new=", row.get("new"))
PY

echo "== re-import one EQ slice via single file= (idempotent) =="
curl -sf -X POST "$BASE/import/csv" \
  -F "file=@${EQUITY_CSVS[-1]};type=text/csv" | tee /tmp/pt-import-eq-re.json

echo "== sync =="
curl -sf -X POST "$BASE/sync" | tee /tmp/pt-sync.json

echo "== portfolio =="
curl -sf "$BASE/portfolio/overview" | tee /tmp/pt-overview.json
curl -sf "$BASE/portfolio/holdings" | tee /tmp/pt-holdings.json
curl -sf "$BASE/portfolio/alerts" | tee /tmp/pt-alerts.json
curl -sf "$BASE/portfolio/performance" | tee /tmp/pt-performance.json

echo "== settings =="
curl -sf "$BASE/settings/benchmarks" | tee /tmp/pt-benchmarks.json

echo "OK — inspect /tmp/pt-*.json and fill live-findings.md"
echo "NOTE: CSV coverage may end before today; gap/reconcile alerts can be expected."
