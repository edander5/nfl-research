"""Inspect by default; --apply provisions roles/ownership without migrating or importing."""
import argparse
import json
import os
from sqlalchemy import create_engine, text
from app.core.config import Settings
from app.db.roles import provision


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    engine = None
    try:
        settings = Settings()
        if settings.db_host != 'db' or settings.db_name != 'nfl_research_dev' or settings.db_purpose != 'migration':
            raise ValueError('admin_override_development_only')
        # Deliberately bootstrap directly; normal runtime engine rejects administrator credentials.
        engine = create_engine(settings.database_url, hide_parameters=True, connect_args={'connect_timeout': 5})
        with engine.begin() as connection:
            if connection.scalar(text('SELECT current_database()')) != 'nfl_research_dev':
                raise ValueError('database_guard')
            if args.apply:
                result = provision(connection, os.environ['ROLE_API_PASSWORD'], os.environ['ROLE_INGEST_PASSWORD'])
            else:
                result = dict(mode='inspection_only', roles=[dict(r._mapping) for r in connection.execute(text(
                    "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin FROM pg_roles WHERE rolname IN ('nfl_owner','nfl_api','nfl_ingest') ORDER BY rolname"))],
                    owners=[dict(r._mapping) for r in connection.execute(text("SELECT tablename,tableowner FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))])
                if connection.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")):
                    result['revision'] = connection.scalar(text('SELECT version_num FROM public.alembic_version'))
        print(json.dumps(result))
        return 0
    except Exception:
        # Never echo SQL, SCRAM verifiers, credentials, exception repr or engine URLs.
        print(json.dumps({'error': 'role_transition_failed', 'hint': 'No automatic retry; review dedicated database, role memberships and secret configuration.'}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
