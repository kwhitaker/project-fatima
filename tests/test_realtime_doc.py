"""Assert that the realtime subscription contract document exists and covers
the key topics required by US-027."""

from pathlib import Path

DOC_PATH = Path(__file__).parent.parent / "docs" / "realtime.md"


def _doc() -> str:
    return DOC_PATH.read_text()


def test_realtime_doc_exists() -> None:
    assert DOC_PATH.exists(), f"Missing realtime doc at {DOC_PATH}"


def test_doc_describes_subscription() -> None:
    text = _doc()
    assert "game_events" in text
    assert "game_id" in text
    assert "filter" in text or "filtered" in text


def test_doc_describes_event_payload() -> None:
    text = _doc()
    assert "event_type" in text
    assert "seq" in text
    assert "payload" in text


def test_doc_describes_seq_ordering() -> None:
    text = _doc()
    assert "seq" in text
    # Ordering guarantee: monotonically increasing or similar wording
    assert "order" in text.lower() or "monoton" in text.lower() or "increment" in text.lower()


def test_doc_describes_mvp_refetch_behaviour() -> None:
    text = _doc()
    assert "GET /games" in text or "GET `/games" in text
    assert "snapshot" in text


def test_doc_covers_all_required_event_types() -> None:
    text = _doc()
    assert "player_joined" in text
    assert "card_placed" in text
    assert "game_forfeited" in text
