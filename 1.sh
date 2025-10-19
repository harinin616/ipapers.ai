#!/usr/bin/env bash
# Postgres FTS Doctor (with progress) for `papers`
# Usage:
#   export DB_OLD=dlmonitor PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD='yourpass'
#   chmod +x fts_doctor_progress.sh && ./fts_doctor_progress.sh
# Optional:
#   FORCE_REBUILD_TSV=1 ./fts_doctor_progress.sh
#   MAINT_WORK_MEM=2GB ./fts_doctor_progress.sh
#   QUERY_WORDS='large & language' ./fts_doctor_progress.sh

set -euo pipefail

: "${DB_OLD:?need DB_OLD}"
: "${PGHOST:?need PGHOST}"
: "${PGPORT:?need PGPORT}"
: "${PGUSER:?need PGUSER}"
: "${PGPASSWORD:?need PGPASSWORD}"

PSQL_BASE=(psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_OLD}")
PSQL="${PSQL_BASE[*]}"

MAINT_WORK_MEM="${MAINT_WORK_MEM:-512MB}"
QUERY_WORDS="${QUERY_WORDS:-large & language}"

# ---------- helpers ----------
run_sql() {  # run quick SQL (no progress)
  ${PSQL_BASE[@]} -Atc "$1"
}

run_cmd_with_app() {  # run a *single* SQL with application_name via PGAPPNAME
  local app="$1"; shift
  PGAPPNAME="$app" ${PSQL_BASE[@]} -c "$*"
}

watch_create_index() {  # poll pg_stat_progress_create_index for given app
  local app="$1"
  while :; do
    local row
    row=$(${PSQL_BASE[@]} -Atc "
      SELECT coalesce(phase,''),
             coalesce(tuples_done,0), coalesce(tuples_total,0),
             coalesce(blocks_done,0),  coalesce(blocks_total,0),
             coalesce(index_relid::regclass::text,'')
      FROM pg_stat_progress_create_index s
      JOIN pg_stat_activity a USING (pid)
      WHERE a.application_name='${app}' LIMIT 1;") || true
    if [[ -n "$row" ]]; then
      IFS='|' read -r phase td tt bd bt idx <<<"$row"
      # 百分比优先用 tuples，其次 blocks
      local pct="?"
      if [[ "$tt" != "0" ]]; then pct=$(( td*100/tt ));
      elif [[ "$bt" != "0" ]]; then pct=$(( bd*100/bt ));
      fi
      echo "[CREATE INDEX] ${phase}  (${pct}%)
  tuples: ${td}/${tt}  blocks: ${bd}/${bt}  index: ${idx}"
    else
      # 可能是 IF NOT EXISTS 已存在，或尚未进入进度视图
      local running
      running=$(run_sql "SELECT count(*) FROM pg_stat_activity WHERE application_name='${app}';")
      if [[ "${running:-0}" == "0" ]]; then
        break
      fi
      echo "[CREATE INDEX] waiting to start..."
    fi
    sleep 2
  done
}

watch_vacuum() {  # poll pg_stat_progress_vacuum for VACUUM VERBOSE
  local app="$1"
  while :; do
    local row
    row=$(${PSQL_BASE[@]} -Atc "
      SELECT coalesce(phase,''),
             coalesce(heap_blks_scanned,0), coalesce(heap_blks_total,0),
             coalesce(heap_blks_vacuumed,0),
             coalesce(index_vacuum_count,0)
      FROM pg_stat_progress_vacuum v
      JOIN pg_stat_activity a USING (pid)
      WHERE a.application_name='${app}' LIMIT 1;") || true
    if [[ -n "$row" ]]; then
      IFS='|' read -r phase scanned total vacu idxv <<<"$row"
      local pct="?"
      if [[ "$total" != "0" ]]; then pct=$(( scanned*100/total )); fi
      echo "[VACUUM] ${phase}  (${pct}%)
  scanned: ${scanned}/${total}  vacuumed: ${vacu}  index_vacuum: ${idxv}"
    else
      local running
      running=$(run_sql "SELECT count(*) FROM pg_stat_activity WHERE application_name='${app}';")
      if [[ "${running:-0}" == "0" ]]; then
        break
      fi
      echo "[VACUUM] waiting to start..."
    fi
    sleep 2
  done
}

spinner() {  # lightweight spinner (for UPDATE，没有内核级进度)
  local msg="$1"; shift
  local pidfile="$1"; shift
  local sp='|/-\'; local i=0
  while [[ -e "$pidfile" ]]; do
    printf "\r%s %s" "$msg" "${sp:i++%${#sp}:1}"
    sleep 0.2
  done
  printf "\r%s done\n" "$msg"
}

# ---------- start ----------
echo "==> Connecting to ${PGUSER}@${PGHOST}:${PGPORT}/${DB_OLD}"
${PSQL_BASE[@]} -Atc "SELECT version();"

echo "==> Ensure required extensions"
${PSQL_BASE[@]} -c "CREATE EXTENSION IF NOT EXISTS unaccent;"
${PSQL_BASE[@]} -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo "==> SET maintenance_work_mem=${MAINT_WORK_MEM}"
${PSQL_BASE[@]} -c "SET maintenance_work_mem='${MAINT_WORK_MEM}';"

echo "==> Check table existence"
TABLE_OK=$(run_sql "SELECT to_regclass('public.papers') IS NOT NULL")
[[ "$TABLE_OK" == "t" ]] || { echo "FATAL: table 'papers' not found"; exit 2; }

echo "==> Ensure column 'tsv' (tsvector) exists"
HAS_TSV=$(run_sql "
  SELECT 1
  FROM pg_attribute a
  JOIN pg_class c ON a.attrelid=c.oid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  JOIN pg_type t ON a.atttypid=t.oid
  WHERE n.nspname='public' AND c.relname='papers'
    AND a.attname='tsv' AND t.typname='tsvector'
    AND a.attnum>0 AND NOT a.attisdropped
  LIMIT 1;") || true
if [[ "${HAS_TSV:-}" != "1" ]]; then
  echo "---- adding tsv column"
  ${PSQL_BASE[@]} -c "ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS tsv tsvector;"
fi

echo "==> Create/replace trigger function for tsv maintenance"
${PSQL_BASE[@]} <<'SQL'
CREATE OR REPLACE FUNCTION papers_tsv_trigger()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.tsv := to_tsvector('simple', unaccent(coalesce(NEW.title,'') || ' ' || coalesce(NEW.abstract,'')));
  RETURN NEW;
END $$;
SQL

echo "==> Ensure trigger on INSERT/UPDATE(title,abstract)"
${PSQL_BASE[@]} -c "DROP TRIGGER IF EXISTS trg_papers_tsv ON public.papers;"
${PSQL_BASE[@]} -c "CREATE TRIGGER trg_papers_tsv
          BEFORE INSERT OR UPDATE OF title, abstract
          ON public.papers
          FOR EACH ROW EXECUTE FUNCTION papers_tsv_trigger();"

echo "==> Backfill/repair tsv values"
NEED=$(run_sql "SELECT count(*) FROM public.papers WHERE tsv IS NULL OR tsv = ''::tsvector;")
if [[ "${FORCE_REBUILD_TSV:-0}" == "1" ]]; then
  echo "---- full rebuild tsv (all rows)"
  # spinner（不切块，不改计划）
  pf=/tmp/.fts_doctor_update.$$; : > "$pf"
  spinner "  updating tsv on all rows..." "$pf" &
  spid=$!
  run_cmd_with_app "fts_doctor:update_all" "
    UPDATE public.papers
    SET tsv = to_tsvector('simple', unaccent(coalesce(title,'') || ' ' || coalesce(abstract,'')));
  "
  rm -f "$pf"; wait $spid || true
else
  echo "---- partial fill (NULL/empty only): ${NEED} rows"
  if [[ "$NEED" != "0" ]]; then
    pf=/tmp/.fts_doctor_update.$$; : > "$pf"
    spinner "  updating tsv on ${NEED} rows..." "$pf" &
    spid=$!
    run_cmd_with_app "fts_doctor:update_needed" "
      UPDATE public.papers
      SET tsv = to_tsvector('simple', unaccent(coalesce(title,'') || ' ' || coalesce(abstract,'')))
      WHERE tsv IS NULL OR tsv = ''::tsvector;
    "
    rm -f "$pf"; wait $spid || true
  else
    echo "  nothing to update."
  fi
fi

echo "==> Ensure GIN index on tsv (CONCURRENTLY, with progress)"
APP1="fts_doctor:create_idx_tsv:$$"
watch_create_index "$APP1" & w1=$!
run_cmd_with_app "$APP1" "
  CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_papers_tsv
  ON public.papers USING GIN (tsv);
"
wait $w1 || true

echo "==> Ensure trigram GIN index on title (CONCURRENTLY, with progress)"
APP2="fts_doctor:create_idx_trgm:$$"
watch_create_index "$APP2" & w2=$!
run_cmd_with_app "$APP2" "
  CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_papers_title_trgm
  ON public.papers USING GIN (title gin_trgm_ops);
"
wait $w2 || true

echo "==> VACUUM ANALYZE papers (with progress)"
APP3="fts_doctor:vacuum:$$"
watch_vacuum "$APP3" & w3=$!
run_cmd_with_app "$APP3" "VACUUM (ANALYZE, VERBOSE) public.papers;"
wait $w3 || true

echo "==> Index usage snapshot"
${PSQL_BASE[@]} -c "
SELECT s.indexrelid::regclass AS index_name,
       s.idx_scan, s.idx_tup_read, s.idx_tup_fetch,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s
JOIN pg_class t ON t.oid = s.relid
WHERE t.relname='papers'
ORDER BY s.idx_scan DESC NULLS LAST;"

echo "==> Quick plan check (expect Bitmap Index Scan)"
${PSQL_BASE[@]} -c "
EXPLAIN
WITH q AS (SELECT to_tsquery('simple', unaccent('${QUERY_WORDS}')) AS qs)
SELECT paper_id, platform
FROM public.papers, q
WHERE tsv @@ q.qs
ORDER BY ts_rank_cd(tsv, q.qs) DESC
LIMIT 10;"

echo "==> Done."
