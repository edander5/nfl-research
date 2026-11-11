"""Owner-only Task 011 grants: inspect by default, --apply changes only approved SELECT ACLs."""
import argparse
import json
from sqlalchemy import create_engine, text
from app.core.config import Settings
from app.db.roles import API_STATS_COLUMNS, grant_api_stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    engine = None
    try:
        settings = Settings()
        if settings.db_host != 'db' or settings.db_name != 'nfl_research_dev' or settings.db_purpose != 'migration':
            raise ValueError('admin_configuration_required')
        engine = create_engine(settings.database_url, hide_parameters=True, connect_args={"connect_timeout": 5})
        with engine.begin() as connection:
            if connection.scalar(text('SELECT current_database()')) != 'nfl_research_dev':
                raise ValueError('database_guard')
            if connection.scalar(text('SELECT version_num FROM public.alembic_version')) != '0002_team_stats':
                raise ValueError('revision_guard')
            # Fixed NOLOGIN owner; only an administrator/authorized owner can assume it.
            connection.exec_driver_sql('SET LOCAL ROLE nfl_owner')
            if args.apply:
                grant_api_stats(connection)
            checks = {table: {column: connection.scalar(text(
                'SELECT has_column_privilege(\'nfl_api\', :table, :column, \'SELECT\')'),
                dict(table='public.'+table, column=column)) for column in columns}
                for table, columns in API_STATS_COLUMNS.items()}
            restrictions = {label: connection.scalar(text(sql)) for label, sql in {
                'raw_records_denied': "SELECT NOT has_column_privilege('nfl_api','public.team_game_stat_revisions','raw_source_record','SELECT')",
                'batch_evidence_denied': "SELECT NOT has_table_privilege('nfl_api','public.team_stats_batches','SELECT')",
                'history_denied': "SELECT NOT has_table_privilege('nfl_api','public.team_stats_selection_events','SELECT')",
                'pointer_writes_denied': "SELECT NOT has_any_column_privilege('nfl_api','public.team_stats_accepted','UPDATE')",
                'history_truncate_denied': "SELECT NOT has_table_privilege('nfl_api','public.team_stats_selection_events','TRUNCATE')",
            }.items()}
            if not all(restrictions.values()):
                raise ValueError('unexpected_api_privileges')
        print(json.dumps(dict(mode='applied' if args.apply else 'inspection_only', column_reads=checks, restrictions=restrictions)))
        return 0
    except Exception:
        print(json.dumps(dict(error='team_stats_api_grant_failed', hint='Stop; check admin configuration, owner role and revision privately.')))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
