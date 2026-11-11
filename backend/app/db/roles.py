"""Explicit administrator-run role provisioning; no calls from application startup."""
import base64
import hashlib
import hmac
import os
from sqlalchemy import text

OWNER = 'nfl_owner'
API = 'nfl_api'
INGEST = 'nfl_ingest'
SCHEDULE = ('teams', 'team_aliases', 'source_artifacts', 'games')
STATS = ('team_stats_batches', 'team_stats_pairs', 'team_game_stat_revisions', 'team_stats_accepted', 'team_stats_selection_events')
TABLES = SCHEDULE + STATS + ('alembic_version',)


def scram_verifier(password):
    # ASCII secrets avoid Unicode SASLprep ambiguity; plaintext never appears in SQL.
    if (not isinstance(password, str) or len(password) < 24 or password.startswith('REPLACE_')
            or any(not 33 <= ord(c) <= 126 for c in password)):
        raise ValueError('use_distinct_random_ascii_passwords_at_least_24_characters')
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 4096)
    stored = hashlib.sha256(hmac.new(salted, b'Client Key', hashlib.sha256).digest()).digest()
    server = hmac.new(salted, b'Server Key', hashlib.sha256).digest()
    b64 = lambda value: base64.b64encode(value).decode()
    return f'SCRAM-SHA-256$4096:{b64(salt)}${b64(stored)}:{b64(server)}'


def provision(connection, api_password, ingestion_password):
    """Caller supplies an explicit admin transaction, only on a dedicated dev/test DB."""
    database = connection.scalar(text('SELECT current_database()'))
    if database not in ('nfl_research_dev', 'nfl_research_test'):
        raise ValueError('database_guard')
    admin = connection.scalar(text('SELECT session_user'))
    if admin in (OWNER, API, INGEST) or not connection.scalar(text('SELECT rolsuper FROM pg_roles WHERE rolname = session_user')):
        raise ValueError('bootstrap_admin_required')
    if api_password == ingestion_password:
        raise ValueError('runtime_passwords_must_differ')
    verifiers = {API: scram_verifier(api_password), INGEST: scram_verifier(ingestion_password)}
    existing = set(connection.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
    if 'team_stats_selection_events' in existing and not connection.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='team_stats_selection_events' AND column_name='generation')")):
        raise ValueError('existing_unhardened_0002_requires_forward_migration')
    functions = set(connection.scalars(text("SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'")))
    if functions - {'team_stats_append_only','team_stats_check_pair','team_stats_check_team','team_stats_check_selection','team_stats_record_selection','team_stats_lock_selection'}:
        raise ValueError('unexpected_public_functions_review_before_transition')
    if existing - set(TABLES):
        raise ValueError('unexpected_public_tables_review_before_transition')
    # Reserved runtime identities must not own unrelated objects in a reused cluster.
    if connection.scalar(text("""SELECT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname IN ('nfl_api','nfl_ingest')
        UNION ALL SELECT 1 FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE r.rolname IN ('nfl_api','nfl_ingest')
        UNION ALL SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE r.rolname IN ('nfl_api','nfl_ingest')
        UNION ALL SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname IN ('nfl_api','nfl_ingest'))""")):
        raise ValueError('runtime_role_owns_objects_review_before_transition')
    for role in (OWNER, API, INGEST):
        if not connection.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:role)'), {'role': role}):
            connection.exec_driver_sql(f'CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT')
        # Refuse unexpected membership instead of guessing what is safe to revoke.
        if connection.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=:role)'), {'role': role}):
            raise ValueError('unexpected_role_membership')
        connection.exec_driver_sql(f'ALTER ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT')
    connection.exec_driver_sql(f'ALTER ROLE {OWNER} NOLOGIN')
    for role, verifier in verifiers.items():
        # Generated verifier alphabet is restricted and contains no quote characters.
        connection.exec_driver_sql(f"ALTER ROLE {role} LOGIN PASSWORD '{verifier}'")
    connection.exec_driver_sql(f'REVOKE CREATE ON DATABASE {database} FROM PUBLIC, nfl_api, nfl_ingest')
    connection.exec_driver_sql('REVOKE ALL ON PARAMETER session_replication_role FROM PUBLIC, nfl_api, nfl_ingest')
    connection.exec_driver_sql(f'ALTER SCHEMA public OWNER TO {OWNER}')
    connection.exec_driver_sql('REVOKE ALL ON SCHEMA public FROM PUBLIC, nfl_api, nfl_ingest')
    connection.exec_driver_sql('GRANT USAGE ON SCHEMA public TO nfl_api, nfl_ingest')
    for table in sorted(existing):
        connection.exec_driver_sql(f'ALTER TABLE public.{table} OWNER TO {OWNER}')
        connection.exec_driver_sql(f'REVOKE ALL ON public.{table} FROM PUBLIC, nfl_api, nfl_ingest')
    # Also revoke prior per-column grants (table-level REVOKE alone is insufficient).
    for row in connection.execute(text("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('teams','team_aliases','source_artifacts','games','team_stats_batches','team_stats_pairs','team_game_stat_revisions','team_stats_accepted','team_stats_selection_events','alembic_version')")):
        connection.exec_driver_sql(f'REVOKE ALL ({row.column_name}) ON public.{row.table_name} FROM PUBLIC, nfl_api, nfl_ingest')
    if 'alembic_version' in existing:
        connection.exec_driver_sql('GRANT SELECT ON public.alembic_version TO nfl_api, nfl_ingest')
    if set(SCHEDULE) <= existing:
        for table in SCHEDULE:
            connection.exec_driver_sql(f'GRANT SELECT ON public.{table} TO nfl_api, nfl_ingest')
            connection.exec_driver_sql(f'GRANT INSERT ON public.{table} TO nfl_ingest')
        connection.exec_driver_sql('GRANT UPDATE ON public.games TO nfl_ingest')
    if set(STATS) <= existing:
        connection.exec_driver_sql('GRANT SELECT ON public.team_stats_selection_events TO nfl_ingest')
        for table in STATS[:-1]:
            connection.exec_driver_sql(f'GRANT SELECT, INSERT ON public.{table} TO nfl_ingest')
        connection.exec_driver_sql('GRANT UPDATE (pair_id, batch_id, generation) ON public.team_stats_accepted TO nfl_ingest')
    # Owner-created future objects must not accidentally become public/executable.
    connection.exec_driver_sql('ALTER DEFAULT PRIVILEGES FOR ROLE nfl_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC')
    connection.exec_driver_sql('ALTER DEFAULT PRIVILEGES FOR ROLE nfl_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC')
    return dict(database=database, schema_owner=OWNER, api_role=API, ingestion_role=INGEST, table_count=len(existing))
