#!/usr/bin/env bash
# finish_v2.sh
# ------------
# Operational closeout for the v2.3 (Pipeline accuracy) rollout — the part of
# "finish v2" that is deterministic and safe to automate. Repeated work is
# driven by loops: a self-test loop, a migrations loop, and a policy-tagged
# rollout-stage loop (gate = abort on fail, soft = warn + continue).
#
# Everything that needs a design / product / QA decision is OUT OF SCOPE and is
# DEFERRED to the new final step v2.11 (printed at the end): the feature
# segments v2.4–v2.10 and the phase-close gates.
#
# Usage:
#   scripts/finish_v2.sh            # self-tests, migrations, geocode, validate
#   scripts/finish_v2.sh --reseed   # also wipe + re-seed Lolla with the new key
#   scripts/finish_v2.sh --scrape   # also refresh lineups+schedules (needs API keys)
#   scripts/finish_v2.sh --yes      # non-interactive (assume yes to prompts)
#
# Requires pipeline/.env (Supabase service-role + API keys). DDL needs a Postgres
# connection: set DATABASE_URL (+ have psql) to auto-apply migrations, otherwise
# the script tells you which files to paste into the Supabase SQL editor.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIPELINE="$ROOT/pipeline"
ENV_FILE="$PIPELINE/.env"

RESEED=0
SCRAPE=0
ASSUME_YES=0
for a in "$@"; do
  case "$a" in
    --reseed)  RESEED=1 ;;
    --scrape)  SCRAPE=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    -h|--help) awk 'NR>1 && /^#/{print} NR>1 && !/^#/{exit}' "$0"; exit 0 ;;
    *) echo "unknown arg: $a (try --help)" >&2; exit 2 ;;
  esac
done

say()  { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok()   { printf '\033[0;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[0;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[0;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
confirm() {
  [ "$ASSUME_YES" = 1 ] && return 0
  read -r -p "$1 [y/N] " r; [ "$r" = y ] || [ "$r" = Y ]
}

# 0. Preflight ---------------------------------------------------------------
say "Preflight"
command -v python3 >/dev/null || die "python3 not found"
[ -f "$ENV_FILE" ] || die "missing $ENV_FILE (Supabase service-role + API keys)"
set -a; . "$ENV_FILE"; set +a
: "${NEXT_PUBLIC_SUPABASE_URL:?set NEXT_PUBLIC_SUPABASE_URL in pipeline/.env}"
: "${SUPABASE_SERVICE_ROLE_KEY:?set SUPABASE_SERVICE_ROLE_KEY in pipeline/.env}"
cd "$PIPELINE"   # python scripts load_dotenv() + run relative to pipeline/
ok "env loaded"

# 1. Offline self-tests (loop; gate before any write) ------------------------
say "Offline self-tests"
for t in \
  "validate_data.py --self-test" \
  "names.py" \
  "dedupe_artists.py --self-test" \
  "geocoder.py" \
  "location_enricher.py --self-test" \
  "test_idempotency.py"; do
  # shellcheck disable=SC2086
  python3 $t || die "self-test failed: $t"
done
ok "all self-tests passed"

# 2. Migrations (loop; DDL — REST/service-role cannot run DDL) ---------------
say "Migrations (v2.3) — apply in order"
MIGS=(
  "$ROOT/db/migrations/20260624_v2_3_3_timezone_and_provenance.sql"
  "$ROOT/db/migrations/20260624_v2_3_4_geocoding.sql"
  "$ROOT/db/migrations/20260624_v2_3_6_lineup_slot_key.sql"
)
if [ -n "${DATABASE_URL:-}" ] && command -v psql >/dev/null; then
  for m in "${MIGS[@]}"; do
    echo "applying $(basename "$m")"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$m"   # all 3 are idempotent
  done
  ok "migrations applied"
else
  warn "no DATABASE_URL/psql — paste these into the Supabase SQL editor IN ORDER:"
  for m in "${MIGS[@]}"; do echo "    db/migrations/$(basename "$m")"; done
  confirm "Already applied in Supabase?" || die "apply the migrations, then re-run"
fi

# 3. Re-seed Lollapalooza (destructive: wipes + rewrites lineup rows) ---------
say "Re-seed Lollapalooza (new key keeps all multi-set rows)"
if [ "$RESEED" = 1 ] && confirm "Wipe + re-seed lollapalooza 2026 lineups from canonical data?"; then
  python3 lolla_schedule_seeder.py --force
else
  warn "skipped — pass --reseed to wipe + rewrite Lolla lineups under the set-grain key"
fi

# 4. Rollout stages (loop; policy-tagged) ------------------------------------
# spec = "policy|label|command"   policy: gate = abort on fail, soft = continue
run_scrape() {                    # scrapers self-loop all festivals; soft per source
  python3 lineup_scraper.py   || warn "lineup_scraper had errors"
  python3 schedule_scraper.py || warn "schedule_scraper had errors"
}

STAGES=(
  "soft|Geocode festivals + seed stages|python3 location_enricher.py"
  "soft|Dedupe report (review what it lists)|python3 dedupe_artists.py"
)
[ "$SCRAPE" = 1 ] && STAGES+=("soft|Refresh lineups + schedules (external APIs)|run_scrape")
STAGES+=("gate|Live validation (success gate)|python3 validate_data.py")  # last

for spec in "${STAGES[@]}"; do
  IFS='|' read -r policy label cmd <<<"$spec"
  say "$label"
  if eval "$cmd"; then
    ok "$label"
  elif [ "$policy" = gate ]; then
    die "$label failed"
  else
    warn "$label failed — continuing"
  fi
done

# Done -----------------------------------------------------------------------
say "v2.3 rollout complete"
cat <<'DEFERRED'
DEFERRED — needs your input (answer the question list), tracked under a new
final step:

  v2.11  Phase finalize & open decisions
         - Resolve the v2.4–v2.10 design/product questions (see question list).
         - Then run phase close (WORKFLOW.md §3), which is gate-driven, not
           scriptable:
           (a) /qa full-app  (b) /code-review ultra  (c) final commit
           (d) merge v2 -> main  (e) delete branches  (f) reconcile docs
           (g) archive planning  (h) brainstorm v3

  Feature segments still to build (each opens once its questions are answered):
    v2.4 Artist page   v2.5 Design system   v2.6 UI rebuild   v2.7 PWA/offline
    v2.8 Phone bg      v2.9 Smart playlists  v2.10 Edge + perf
DEFERRED
