from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core.config import Settings


def make_engine(settings: Settings):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c timezone=UTC"},
    )

    @event.listens_for(engine, "connect")
    def enforce_role(connection, _):
        with connection.cursor() as cursor:
            if settings.db_purpose == 'migration':
                cursor.execute('SET ROLE nfl_owner')
            else:
                cursor.execute("""SELECT current_user = session_user AND current_user IN ('nfl_api','nfl_ingest') AND NOT (r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls)
                    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                                    WHERE n.nspname='public' AND pg_catalog.pg_has_role(r.oid,c.relowner,'MEMBER'))
                    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles o WHERE o.rolname='nfl_owner'
                                    AND pg_catalog.pg_has_role(r.oid,o.oid,'MEMBER'))
                    AND NOT pg_catalog.has_schema_privilege(current_user,'public','CREATE')
                    AND NOT pg_catalog.has_database_privilege(current_user,current_database(),'CREATE')
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user""")
                if cursor.fetchone() != (True,):
                    raise ValueError('restricted_runtime_role_required')
        # Do not leak the role-check SELECT's implicit transaction to a caller's transaction.
        connection.commit()
    return engine


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session
