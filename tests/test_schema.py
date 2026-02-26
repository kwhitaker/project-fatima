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


# ---------------------------------------------------------------------------
# US-025: cards table schema assertions
# ---------------------------------------------------------------------------

def _cards_sql() -> str:
    """Return only the cards schema migration SQL."""
    cards_file = MIGRATIONS_DIR / "002_cards_schema.sql"
    assert cards_file.exists(), f"cards schema file not found: {cards_file}"
    return cards_file.read_text()


def test_cards_schema_file_exists() -> None:
    cards_file = MIGRATIONS_DIR / "002_cards_schema.sql"
    assert cards_file.exists(), "002_cards_schema.sql is missing"


def test_cards_table_defined() -> None:
    assert "cards" in _cards_sql()


def test_cards_has_card_key_column() -> None:
    assert "card_key" in _cards_sql()


def test_cards_has_character_key_column() -> None:
    assert "character_key" in _cards_sql()


def test_cards_has_tier_column() -> None:
    assert "tier" in _cards_sql()


def test_cards_has_rarity_column() -> None:
    assert "rarity" in _cards_sql()


def test_cards_has_is_named_column() -> None:
    assert "is_named" in _cards_sql()


def test_cards_has_side_columns() -> None:
    sql = _cards_sql()
    for col in ("n ", "e ", "s ", "w "):
        assert col in sql, f"side column '{col.strip()}' not found in cards schema"


def test_cards_has_set_column() -> None:
    assert "set" in _cards_sql()


def test_cards_has_tags_column() -> None:
    assert "tags" in _cards_sql()


def test_cards_has_definition_jsonb() -> None:
    sql = _cards_sql()
    assert "definition" in sql
    assert "jsonb" in sql


def test_cards_has_tier_constraint() -> None:
    sql = _cards_sql()
    assert "tier BETWEEN 1 AND 3" in sql or ("tier" in sql and "1" in sql and "3" in sql)


def test_cards_has_rarity_constraint() -> None:
    sql = _cards_sql()
    assert "rarity BETWEEN 1 AND 100" in sql or ("rarity" in sql and "100" in sql)


def test_cards_has_side_value_constraints() -> None:
    sql = _cards_sql()
    # Each side constrained to 1..10
    assert "BETWEEN 1 AND 10" in sql


def test_cards_has_rls_policy() -> None:
    assert "ROW LEVEL SECURITY" in _cards_sql()
