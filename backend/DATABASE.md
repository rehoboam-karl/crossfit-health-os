# Database Recovery Runbook

Practical guide for recreating the `crossfit` Postgres database from scratch and dealing with the role/grant pitfalls this project has hit before.

## Current state (snapshot)

- **Host:** `100.105.21.37` (deploy server, accessible over Tailscale)
- **Port:** `5432` (host postgres, NOT a container — `systemctl status postgresql`)
- **DB:** `crossfit`
- **App role:** `crossfit` (LOGIN, not superuser)
- **DBA role:** `postgres` (superuser, owns most legacy tables)
- **Alembic head:** `0009realign_mealogs`
- **Connection string used by the app:**
  `postgresql://crossfit:CrossFit2024!@100.105.21.37:5432/crossfit`

The `.env` is the source of truth for `DATABASE_URL`. `app/db/database.py` and `app/db/session.py` read it via `app.core.config.settings` (with `os.environ` taking precedence — for docker-compose / systemd overrides).

## Recreate from scratch

Run on the host that owns the Postgres instance (i.e. `ssh root@100.105.21.37`).

### 1. Create role and database

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE crossfit WITH LOGIN PASSWORD 'CrossFit2024!';
CREATE DATABASE crossfit OWNER crossfit;
SQL
```

> If you want the app role to own the schema (cleanest setup, avoids the grant pain in step 3), make `crossfit` the DB owner from the start as shown above. Don't create the database as `postgres` and migrate it later — that's how we ended up with mixed ownership.

### 2. Apply migrations

From a checkout where `backend/alembic/` exists. The DB URL passed via env wins over `alembic.ini`'s default.

```bash
cd backend
DATABASE_URL='postgresql://crossfit:CrossFit2024!@100.105.21.37:5432/crossfit' \
  ./venv/bin/alembic upgrade head
```

Verify head:

```bash
DATABASE_URL='...' ./venv/bin/alembic current
# expected: 0009realign_mealogs (head)
```

### 3. Fix grants (only if the DB ended up with mixed ownership)

If migrations were ever run as a different role (e.g. `postgres` ran the early migrations and `crossfit` ran the later ones — the situation we inherited), the app will get `permission denied for table ...` on the tables owned by the other role.

The current production DB has 19 tables owned by `postgres` and 5 owned by `crossfit`. Until that's reconciled, `crossfit` needs explicit grants:

```bash
ssh root@100.105.21.37 "sudo -u postgres psql -d crossfit" <<'SQL'
GRANT USAGE ON SCHEMA public TO crossfit;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO crossfit;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO crossfit;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO crossfit;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO crossfit;
SQL
```

The `ALTER DEFAULT PRIVILEGES` lines are the important ones — without them, any future table created by `postgres` will lock `crossfit` out again.

### 3b. (Optional, cleaner) Reassign ownership instead of granting

If no other tenant relies on those tables, the durable fix is to make `crossfit` own everything:

```sql
REASSIGN OWNED BY postgres TO crossfit;
```

Caveat: this also moves any other objects `postgres` happens to own in this DB. Inspect first:

```sql
SELECT n.nspname, c.relname, c.relkind
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r ON r.oid = c.relowner
WHERE r.rolname = 'postgres' AND n.nspname = 'public';
```

After reassignment, future `ALTER TABLE` statements in migrations work without superuser.

### 4. Seed data

There is no DB-level seed step. The movement library lives in code at `backend/app/schema/v2/movements_seed.py` and is loaded in-memory by `MovementLibrary.load_default_library()`. Workout templates are user-generated.

User accounts: register via the API (`POST /api/v1/auth/register`).

## Verification

```bash
# 1. Connection works
./venv/bin/python -c "
import psycopg2
c = psycopg2.connect('postgresql://crossfit:CrossFit2024!@100.105.21.37:5432/crossfit')
cur = c.cursor()
cur.execute('SELECT count(*) FROM information_schema.tables WHERE table_schema=%s', ('public',))
print('public tables:', cur.fetchone()[0])  # expected: 24
cur.execute('SELECT version_num FROM alembic_version')
print('alembic head:', cur.fetchone()[0])   # expected: 0009realign_mealogs
"

# 2. App role can DML on tables owned by other roles (this is what was broken)
./venv/bin/python -c "
import psycopg2
c = psycopg2.connect('postgresql://crossfit:CrossFit2024!@100.105.21.37:5432/crossfit')
cur = c.cursor()
for t in ('meal_logs', 'users', 'user_stats', 'workout_templates'):
    cur.execute(f'SELECT count(*) FROM {t}')
    print(t, cur.fetchone()[0])
"

# 3. App boots cleanly — no '127.0.0.1:5432 refused' in startup log
cd backend && ./venv/bin/python -m uvicorn app.main:app --port 8001 2>&1 | head -10
```

## Troubleshooting

### `permission denied for table <X>`
Role `crossfit` lacks DML on a table owned by another role. Run step 3 again — note `ALL TABLES IN SCHEMA` only covers tables that exist *at run time*. If a new migration created a table while running as `postgres`, you need to re-apply the GRANT (or have the `ALTER DEFAULT PRIVILEGES` from step 3 in place beforehand).

### Startup logs `Could not initialize database: connection ... 127.0.0.1 ... refused`
Old bug, fixed in commit `5558107`. If you see it again, it means something is calling `os.getenv("DATABASE_URL", "<localhost default>")` — search the codebase for that pattern. The correct call is `os.getenv("DATABASE_URL") or settings.DATABASE_URL`.

### `/health` lies
`GET /health` is hardcoded in `backend/app/main.py` to return `database: connected` regardless. Don't trust it as a DB-up signal. To actually verify, hit any auth-required endpoint with a valid JWT — a 500 with a Postgres traceback in `/tmp/crossfit_health_os.log` is the real diagnostic.

### Local app can't reach the remote DB
Postgres on the deploy server listens on `0.0.0.0:5432`. From a new client, check:
- Tailscale up? `tailscale status` should list the deploy host.
- `pg_hba.conf` allows the source IP/network? On the deploy host:
  `sudo -u postgres psql -c "SHOW hba_file"` then inspect that file. The relevant line should be `host crossfit crossfit <network>/<mask> scram-sha-256` (or `md5`).

## Schema reference

A fresh schema dump can be generated with:

```bash
ssh root@100.105.21.37 \
  "sudo -u postgres pg_dump -d crossfit --schema-only --no-owner --no-privileges" \
  > /tmp/crossfit-schema.sql
```

Treat `backend/alembic/versions/` as the source of truth, not the dump — the dump is for diffing and emergency reference.
