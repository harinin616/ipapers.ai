#!/usr/bin/env bash
set -euo pipefail

# ========= 源库连接（export）=========
DB_OLD="${DB_OLD:-dlmonitor}"
PGUSER="${PGUSER:-postgres}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGPASSWORD="${PGPASSWORD:-}"   # 或 ~/.pgpass

# ========= 目标库连接（import）=========
DB_NEW="${DB_NEW:-$DB_OLD}"
NEW_PGUSER="${NEW_PGUSER:-postgres}"
NEW_PGHOST="${NEW_PGHOST:-localhost}"
NEW_PGPORT="${NEW_PGPORT:-5432}"
NEW_PGPASSWORD="${NEW_PGPASSWORD:-$PGPASSWORD}"

psql_src() { PGPASSWORD="$PGPASSWORD" psql -X -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_OLD" "$@"; }
psql_dst() { PGPASSWORD="$NEW_PGPASSWORD" psql -X -v ON_ERROR_STOP=1 -h "$NEW_PGHOST" -p "$NEW_PGPORT" -U "$NEW_PGUSER" -d "$DB_NEW" "$@"; }

usage() {
  cat <<'USAGE'
Usage:
  # 源机导出剩余表
  ./migrate_rest.sh export [OUTDIR]

  # 目标机导入
  ./migrate_rest.sh import /abs/path/to/OUTDIR
USAGE
}

cmd="${1:-}"; shift || true

case "$cmd" in
# ====================== EXPORT ======================
  export)
    OUTDIR="${1:-dump_rest_$(date +%Y%m%d_%H%M%S)}"; mkdir -p "$OUTDIR"
    echo ">> Exporting remaining tables -> $OUTDIR"

    psql_src -c "COPY (SELECT id::text, legacy_user_id, name, email FROM users ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/users.csv"
    psql_src -c "COPY (SELECT session_id, user_id::text, title, created_at, last_message_at FROM sessions ORDER BY session_id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/sessions.csv"
    psql_src -c "COPY (SELECT message_id, session_id, content, created_at, role FROM messages ORDER BY message_id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/messages.csv"
    psql_src -c "COPY (SELECT id, user_id::text, name, created_at FROM folders ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/folders.csv"
    psql_src -c "COPY (SELECT id, folder_id, paper_id, COALESCE(NULLIF(TRIM(platform),''),'arxiv') AS platform, added_at, selected FROM user_files ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/user_files.csv"
    psql_src -c "COPY (SELECT id, folder_id, owner_id::text, is_public, created_at, summary, allowed_user_ids::text, allowed_editor_ids::text FROM shared_folders ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/shared_folders.csv"
    psql_src -c "COPY (SELECT shared_folder_id, comment_id FROM shared_folder_comments ORDER BY shared_folder_id, comment_id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/shared_folder_comments.csv"
    psql_src -c "COPY (SELECT id, content, created_at, commenter_id::text, commenter_name FROM comments ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/comments.csv"
    psql_src -c "COPY (SELECT paper_id, COALESCE(NULLIF(TRIM(platform),''),'arxiv') AS platform, comment_id FROM paper_comments ORDER BY paper_id, platform, comment_id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/paper_comments.csv"
    psql_src -c "COPY (SELECT user_id::text, topic FROM user_topics ORDER BY user_id, topic) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/user_topics.csv"
    psql_src -c "COPY (SELECT grant_id, title, agency, synopsis, detail_url, posted_date, updated_date, close_date, status, embedding::text FROM grants ORDER BY grant_id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/grants.csv"
    psql_src -c "COPY (SELECT email FROM email_list ORDER BY email) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/email_list.csv"
    psql_src -c "COPY (SELECT day, cnt FROM page_view_daily ORDER BY day) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/page_view_daily.csv"
    psql_src -c "COPY (SELECT id, question, email, user_id::text, created_at FROM feedback ORDER BY id) TO STDOUT WITH (FORMAT CSV, HEADER true)" > "$OUTDIR/feedback.csv"

    echo ">> Export done."
    ls -lh "$OUTDIR"/*.csv
    ;;

# ====================== IMPORT ======================
  import)
    DIR="${1:-}"; [[ -n "$DIR" ]] || { usage; exit 1; }

    if command -v realpath >/dev/null 2>&1; then DIR_ABS="$(realpath "$DIR")"; else pushd "$DIR" >/dev/null; DIR_ABS="$(pwd -P)"; popd >/dev/null; fi
    echo ">> Importing from $DIR_ABS into $NEW_PGUSER@$NEW_PGHOST:$NEW_PGPORT/$DB_NEW"

    psql_dst <<SQL
\\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = 0;
CREATE EXTENSION IF NOT EXISTS vector;

-- helper：对齐序列/identity
CREATE OR REPLACE FUNCTION _align_seq(tbl regclass, col name) RETURNS void AS \$\$
DECLARE seq_name text; max_id bigint;
BEGIN
  SELECT pg_get_serial_sequence(tbl::text, col) INTO seq_name;
  IF seq_name IS NOT NULL THEN
    EXECUTE format('SELECT COALESCE(MAX(%I),0) FROM %s', col, tbl) INTO max_id;
    EXECUTE format('SELECT setval(%L, %s, true)', seq_name, max_id);
  ELSE
    EXECUTE format('SELECT COALESCE(MAX(%I),0)+1 FROM %s', col, tbl) INTO max_id;
    BEGIN
      EXECUTE format('ALTER TABLE %s ALTER COLUMN %I RESTART WITH %s', tbl, col, max_id);
    EXCEPTION WHEN others THEN NULL;
    END;
  END IF;
END
\$\$ LANGUAGE plpgsql;

-- ========= 0) 用户映射 =========
CREATE TEMP TABLE _stg_users(id text, legacy_user_id text, name text, email text);
\\copy _stg_users FROM '${DIR_ABS}/users.csv' CSV HEADER;

CREATE TEMP TABLE _users_parsed AS
SELECT
  (id)::uuid                           AS src_id,
  NULLIF(legacy_user_id,'')::bigint    AS legacy_user_id,
  NULLIF(name,'')                      AS name,
  NULLIF(email,'')                     AS email
FROM _stg_users;

CREATE TEMP TABLE _map_user(src_id uuid PRIMARY KEY, dst_id uuid NOT NULL);

-- 已存在 legacy_user_id -> 复用
INSERT INTO _map_user(src_id, dst_id)
SELECT u.src_id, t.id
FROM _users_parsed u
JOIN users t ON t.legacy_user_id = u.legacy_user_id
WHERE u.legacy_user_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- 已存在 UUID -> 恒等
INSERT INTO _map_user(src_id, dst_id)
SELECT u.src_id, u.src_id
FROM _users_parsed u
JOIN users t ON t.id = u.src_id
ON CONFLICT DO NOTHING;

-- 其余尝试插入（email 冲突置 NULL）
WITH to_ins AS (
  SELECT u.*
  FROM _users_parsed u
  LEFT JOIN _map_user m ON m.src_id = u.src_id
  WHERE m.src_id IS NULL
)
INSERT INTO users(id, legacy_user_id, name, email)
SELECT
  u.src_id,
  u.legacy_user_id,
  u.name,
  CASE
    WHEN u.email IS NULL THEN NULL
    WHEN EXISTS (SELECT 1 FROM users x WHERE x.email = u.email) THEN NULL
    ELSE u.email
  END
FROM to_ins u;

-- 补映射
INSERT INTO _map_user(src_id, dst_id)
SELECT u.src_id, u.src_id
FROM _users_parsed u
LEFT JOIN _map_user m ON m.src_id = u.src_id
WHERE m.src_id IS NULL;

SELECT _align_seq('users','legacy_user_id');

-- ========= 1) sessions =========
CREATE TEMP TABLE _stg_sessions(session_id text, user_id text, title text, created_at timestamp, last_message_at timestamp);
\\copy _stg_sessions FROM '${DIR_ABS}/sessions.csv' CSV HEADER;
INSERT INTO sessions(session_id, user_id, title, created_at, last_message_at)
SELECT s.session_id,
       COALESCE(m.dst_id, (s.user_id)::uuid),
       COALESCE(NULLIF(s.title,''),'untitled'),
       s.created_at, s.last_message_at
FROM _stg_sessions s
LEFT JOIN _map_user m ON m.src_id = (s.user_id)::uuid
JOIN users u ON u.id = COALESCE(m.dst_id, (s.user_id)::uuid)
LEFT JOIN sessions t ON t.session_id = s.session_id
WHERE t.session_id IS NULL;

-- ========= 2) messages =========
CREATE TEMP TABLE _stg_messages(message_id bigint, session_id text, content text, created_at timestamp, role text);
\\copy _stg_messages FROM '${DIR_ABS}/messages.csv' CSV HEADER;
INSERT INTO messages(message_id, session_id, content, created_at, role)
SELECT m.message_id, m.session_id, m.content, m.created_at, m.role
FROM _stg_messages m
JOIN sessions s ON s.session_id = m.session_id
LEFT JOIN messages t ON t.message_id = m.message_id
WHERE t.message_id IS NULL;
SELECT _align_seq('messages','message_id');

-- ========= 3) folders =========
CREATE TEMP TABLE _stg_folders(id bigint, user_id text, name text, created_at timestamp);
\\copy _stg_folders FROM '${DIR_ABS}/folders.csv' CSV HEADER;
INSERT INTO folders(id, user_id, name, created_at)
SELECT f.id,
       COALESCE(m.dst_id, (f.user_id)::uuid),
       COALESCE(NULLIF(f.name,''),'default'),
       f.created_at
FROM _stg_folders f
LEFT JOIN _map_user m ON m.src_id = (f.user_id)::uuid
JOIN users u ON u.id = COALESCE(m.dst_id, (f.user_id)::uuid)
LEFT JOIN folders t ON t.id = f.id
WHERE t.id IS NULL;
SELECT _align_seq('folders','id');

-- ========= 4) shared_folders（含数组映射） =========
CREATE TEMP TABLE _stg_sf(
  id bigint, folder_id bigint, owner_id text, is_public text, created_at timestamp, summary text,
  allowed_user_ids text, allowed_editor_ids text
);
\\copy _stg_sf FROM '${DIR_ABS}/shared_folders.csv' CSV HEADER;

CREATE TEMP TABLE _sf_parsed AS
SELECT
  s.id, s.folder_id,
  COALESCE(mu.dst_id, (s.owner_id)::uuid) AS owner_id,
  COALESCE(NULLIF(s.is_public,''),'t')::boolean AS is_public,
  s.created_at, s.summary,
  (
    SELECT COALESCE(array_agg(COALESCE(m2.dst_id, elem)), ARRAY[]::uuid[])
    FROM unnest(COALESCE(NULLIF(s.allowed_user_ids,'')::uuid[], ARRAY[]::uuid[])) AS elem
    LEFT JOIN _map_user m2 ON m2.src_id = elem
  ) AS allowed_user_ids,
  (
    SELECT COALESCE(array_agg(COALESCE(m3.dst_id, elem)), ARRAY[]::uuid[])
    FROM unnest(COALESCE(NULLIF(s.allowed_editor_ids,'')::uuid[], ARRAY[]::uuid[])) AS elem
    LEFT JOIN _map_user m3 ON m3.src_id = elem
  ) AS allowed_editor_ids
FROM _stg_sf s
LEFT JOIN _map_user mu ON mu.src_id = (s.owner_id)::uuid;

INSERT INTO shared_folders(id, folder_id, owner_id, is_public, created_at, summary, allowed_user_ids, allowed_editor_ids)
SELECT p.id, p.folder_id, p.owner_id, p.is_public, p.created_at, p.summary, p.allowed_user_ids, p.allowed_editor_ids
FROM _sf_parsed p
JOIN folders f ON f.id = p.folder_id
JOIN users u   ON u.id = p.owner_id
LEFT JOIN shared_folders t ON t.id = p.id
WHERE t.id IS NULL;
SELECT _align_seq('shared_folders','id');

-- ========= 5) comments =========
CREATE TEMP TABLE _stg_comments(id bigint, content text, created_at timestamp, commenter_id text, commenter_name text);
\\copy _stg_comments FROM '${DIR_ABS}/comments.csv' CSV HEADER;
INSERT INTO comments(id, content, created_at, commenter_id, commenter_name)
SELECT c.id, c.content, c.created_at,
       CASE WHEN NULLIF(c.commenter_id,'') IS NULL
            THEN NULL
            ELSE COALESCE(m.dst_id, (c.commenter_id)::uuid) END,
       COALESCE(c.commenter_name,'')
FROM _stg_comments c
LEFT JOIN _map_user m ON (NULLIF(c.commenter_id,'') IS NOT NULL AND m.src_id = (c.commenter_id)::uuid)
LEFT JOIN comments t ON t.id = c.id
WHERE t.id IS NULL;
SELECT _align_seq('comments','id');

-- ========= 6) shared_folder_comments =========
CREATE TEMP TABLE _stg_sfc(shared_folder_id bigint, comment_id bigint);
\\copy _stg_sfc FROM '${DIR_ABS}/shared_folder_comments.csv' CSV HEADER;
INSERT INTO shared_folder_comments(shared_folder_id, comment_id)
SELECT s.shared_folder_id, s.comment_id
FROM _stg_sfc s
JOIN shared_folders sf ON sf.id = s.shared_folder_id
JOIN comments c        ON c.id = s.comment_id
LEFT JOIN shared_folder_comments t
  ON t.shared_folder_id = s.shared_folder_id AND t.comment_id = s.comment_id
WHERE t.shared_folder_id IS NULL;

-- ========= 7) paper_comments =========
CREATE TEMP TABLE _stg_pc(paper_id text, platform text, comment_id bigint);
\\copy _stg_pc FROM '${DIR_ABS}/paper_comments.csv' CSV HEADER;
INSERT INTO paper_comments(paper_id, platform, comment_id)
SELECT TRIM(p.paper_id),
       COALESCE(NULLIF(TRIM(p.platform),''),'arxiv'),
       p.comment_id
FROM _stg_pc p
JOIN papers   pp ON pp.paper_id = TRIM(p.paper_id) AND pp.platform = COALESCE(NULLIF(TRIM(p.platform),''),'arxiv')
JOIN comments cc ON cc.id = p.comment_id
LEFT JOIN paper_comments t
  ON t.paper_id = TRIM(p.paper_id)
 AND t.platform = COALESCE(NULLIF(TRIM(p.platform),''),'arxiv')
 AND t.comment_id = p.comment_id
WHERE t.paper_id IS NULL;

-- ========= 8) user_files =========
CREATE TEMP TABLE _stg_uf(id bigint, folder_id bigint, paper_id text, platform text, added_at timestamp, selected text);
\\copy _stg_uf FROM '${DIR_ABS}/user_files.csv' CSV HEADER;
INSERT INTO user_files(id, folder_id, paper_id, platform, added_at, selected)
SELECT u.id, u.folder_id, TRIM(u.paper_id),
       COALESCE(NULLIF(TRIM(u.platform),''),'arxiv'),
       u.added_at, COALESCE(NULLIF(u.selected,''),'f')::boolean
FROM _stg_uf u
JOIN folders f ON f.id = u.folder_id
JOIN papers  p ON p.paper_id = TRIM(u.paper_id) AND p.platform = COALESCE(NULLIF(TRIM(u.platform),''),'arxiv')
LEFT JOIN user_files t ON t.id = u.id
WHERE t.id IS NULL;
SELECT _align_seq('user_files','id');

-- ========= 9) user_topics =========
CREATE TEMP TABLE _stg_ut(user_id text, topic text);
\\copy _stg_ut FROM '${DIR_ABS}/user_topics.csv' CSV HEADER;
INSERT INTO user_topics(user_id, topic)
SELECT COALESCE(m.dst_id, (u.user_id)::uuid), u.topic
FROM _stg_ut u
LEFT JOIN _map_user m ON m.src_id = (u.user_id)::uuid
JOIN users x ON x.id = COALESCE(m.dst_id, (u.user_id)::uuid)
LEFT JOIN user_topics t ON t.user_id = COALESCE(m.dst_id, (u.user_id)::uuid) AND t.topic = u.topic
WHERE t.user_id IS NULL;

-- ========= 10) grants =========
CREATE TEMP TABLE _stg_grants(
  grant_id text, title text, agency text, synopsis text, detail_url text,
  posted_date timestamp, updated_date timestamp, close_date timestamp,
  status text, embedding text
);
\\copy _stg_grants FROM '${DIR_ABS}/grants.csv' CSV HEADER;
INSERT INTO grants(grant_id, title, agency, synopsis, detail_url,
                   posted_date, updated_date, close_date, status, embedding)
SELECT g.grant_id, g.title, g.agency, g.synopsis, g.detail_url,
       g.posted_date, g.updated_date, g.close_date, g.status,
       NULLIF(g.embedding,'')::vector
FROM _stg_grants g
LEFT JOIN grants t ON t.grant_id = g.grant_id
WHERE t.grant_id IS NULL;

-- ========= 11) email_list（自适应 created_at NOT NULL） =========
CREATE TEMP TABLE _stg_email(email text);
\\copy _stg_email FROM '${DIR_ABS}/email_list.csv' CSV HEADER;

DO \$\$
DECLARE has_created_at boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = ANY (current_schemas(true))
      AND table_name   = 'email_list'
      AND column_name  = 'created_at'
  ) INTO has_created_at;

  IF has_created_at THEN
    -- 目标表有 created_at（可能 NOT NULL），统一补 now()
    EXECUTE 'INSERT INTO email_list(email, created_at)
             SELECT e.email, now()
             FROM _stg_email e
             LEFT JOIN email_list t ON t.email = e.email
             WHERE t.email IS NULL';
  ELSE
    -- 目标表无 created_at
    EXECUTE 'INSERT INTO email_list(email)
             SELECT e.email
             FROM _stg_email e
             LEFT JOIN email_list t ON t.email = e.email
             WHERE t.email IS NULL';
  END IF;
END
\$\$;

-- ========= 12) page_view_daily =========
CREATE TEMP TABLE _stg_pvd(day date, cnt bigint);
\\copy _stg_pvd FROM '${DIR_ABS}/page_view_daily.csv' CSV HEADER;
UPDATE page_view_daily p
SET cnt = GREATEST(p.cnt, s.cnt)
FROM _stg_pvd s
WHERE p.day = s.day;
INSERT INTO page_view_daily(day, cnt)
SELECT s.day, s.cnt
FROM _stg_pvd s
LEFT JOIN page_view_daily p ON p.day = s.day
WHERE p.day IS NULL;

-- ========= 13) feedback（映射 user_id） =========
CREATE TEMP TABLE _stg_fb(id bigint, question text, email text, user_id text, created_at timestamp);
\\copy _stg_fb FROM '${DIR_ABS}/feedback.csv' CSV HEADER;
INSERT INTO feedback(id, question, email, user_id, created_at)
SELECT f.id, f.question, f.email,
       CASE WHEN NULLIF(f.user_id,'') IS NULL THEN NULL
            ELSE COALESCE(m.dst_id, (f.user_id)::uuid) END,
       f.created_at
FROM _stg_fb f
LEFT JOIN _map_user m ON (NULLIF(f.user_id,'') IS NOT NULL AND m.src_id = (f.user_id)::uuid)
LEFT JOIN feedback t ON t.id = f.id
WHERE t.id IS NULL;
SELECT _align_seq('feedback','id');

COMMIT;

-- Sanity（都应为 0）
\\echo 'Sanity: paper_comments without paper ->'
SELECT COUNT(*) FROM paper_comments pc
LEFT JOIN papers p ON p.paper_id=pc.paper_id AND p.platform=pc.platform
WHERE p.paper_id IS NULL;

\\echo 'Sanity: shared_folder_comments without endpoints ->'
SELECT COUNT(*) FROM shared_folder_comments sfc
LEFT JOIN shared_folders sf ON sf.id=sfc.shared_folder_id
LEFT JOIN comments c ON c.id=sfc.comment_id
WHERE sf.id IS NULL OR c.id IS NULL;

\\echo 'Sanity: user_files without endpoints ->'
SELECT COUNT(*) FROM user_files uf
LEFT JOIN folders f ON f.id=uf.folder_id
LEFT JOIN papers  p ON p.paper_id=uf.paper_id AND p.platform=uf.platform
WHERE f.id IS NULL OR p.paper_id IS NULL;
SQL

    echo ">> Import done."
    ;;

  ""|-h|--help|help) usage ;;
  *) echo "Unknown command: $cmd"; usage; exit 2;;
esac
