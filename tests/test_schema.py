from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent.parent / "supabase" / "migrations"


def _all_sql() -> str:
    return "\n".join(f.read_text() for f in sorted(MIGRATIONS_DIR.glob("*.sql")))


def test_migration_files_exist() -> None:
    files = list(MIGRATIONS_DIR.glob("*.sql"))
    assert len(files) >= 1, f"No .sql files found in {MIGRATIONS_DIR}"


def test_schema_has_profiles_table() -> None:
    assert "profiles" in _all_sql()


def test_schema_has_games_table() -> None:
    assert "games" in _all_sql()


def test_schema_has_game_events_table() -> None:
    assert "game_events" in _all_sql()


def test_schema_has_current_state_column() -> None:
    assert "current_state" in _all_sql()


def test_schema_has_state_version_column() -> None:
    assert "state_version" in _all_sql()


def test_schema_has_seq_column() -> None:
    # seq orders events per game_id
    assert "seq" in _all_sql()


def test_schema_enables_rls() -> None:
    assert "ROW LEVEL SECURITY" in _all_sql()
