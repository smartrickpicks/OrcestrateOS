import os
import glob
import logging
import psycopg2

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def _ensure_schema_migrations(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
    conn.commit()


def _get_applied(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version;")
        return set(row[0] for row in cur.fetchall())


def _discover_migrations():
    pattern = os.path.join(MIGRATIONS_DIR, "*.sql")
    files = sorted(glob.glob(pattern))
    migrations = []
    for filepath in files:
        filename = os.path.basename(filepath)
        version = filename.split("_", 1)[0]
        migrations.append((version, filename, filepath))
    return migrations


def run_migrations(database_url=None):
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    conn = psycopg2.connect(database_url)
    try:
        _ensure_schema_migrations(conn)
        applied = _get_applied(conn)
        migrations = _discover_migrations()

        seed_enabled = os.environ.get("SEED_DATA", "").lower() == "true"

        applied_count = 0
        for version, filename, filepath in migrations:
            if version in applied:
                logger.info("Migration %s already applied, skipping", filename)
                continue

            if "seed" in filename.lower() and not seed_enabled:
                logger.info("Skipping seed migration %s (SEED_DATA != true)", filename)
                continue

            logger.info("Applying migration: %s", filename)
            with open(filepath, "r") as f:
                sql = f.read()

            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s);",
                    (version,)
                )
            conn.commit()
            applied_count += 1
            logger.info("Migration %s applied successfully", filename)

        if applied_count == 0:
            logger.info("All migrations already applied")
        else:
            logger.info("Applied %d migration(s)", applied_count)

    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_migrations()
