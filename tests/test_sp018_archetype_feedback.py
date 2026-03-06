"""Tests for US-SP-018: archetype_used_name and intimidate_target_cell in LastMoveInfo.

Backend portion: verify that apply_intent sets these fields correctly.
"""

from random import Random

import pytest

from app.models.game import Archetype, BoardCell, LastMoveInfo
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card, make_state


def _card_lookup(*cards):
    return {c.card_key: c for c in cards}


class TestArchetypeUsedName:
    @pytest.mark.parametrize(
        "archetype,extra_kwargs,expected_name",
        [
            (Archetype.SKULKER, {"skulker_boost_side": "n"}, "skulker"),
            (Archetype.MARTIAL, {"martial_rotation_direction": "cw"}, "martial"),
            (Archetype.CASTER, {}, "caster"),
            (Archetype.INTIMIDATE, {"intimidate_target_cell": 1}, "intimidate"),
        ],
    )
    def test_archetype_used_name_set_on_power_use(
        self, archetype, extra_kwargs, expected_name
    ):
        c1 = make_card("c1", n=5, e=5, s=5, w=5)
        c2 = make_card("c2", n=3, e=3, s=3, w=3)
        board = [None] * 9
        if archetype == Archetype.INTIMIDATE:
            board[1] = BoardCell(card_key="c2", owner=1)
        state = make_state(
            board=board,
            p0_hand=["c1"],
            p0_archetype=archetype,
            p1_hand=["c2"],
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="c1",
            cell_index=0,
            use_archetype=True,
            **extra_kwargs,
        )
        result = apply_intent(state, intent, _card_lookup(c1, c2), rng=Random(42))
        assert result.last_move is not None
        assert result.last_move.archetype_used_name == expected_name

    def test_archetype_used_name_null_when_no_power(self):
        c1 = make_card("c1")
        state = make_state(
            p0_hand=["c1"],
            p0_archetype=Archetype.SKULKER,
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0, card_key="c1", cell_index=0, use_archetype=False
        )
        result = apply_intent(state, intent, _card_lookup(c1), rng=Random(42))
        assert result.last_move is not None
        assert result.last_move.archetype_used_name is None

    def test_devout_archetype_used_name_on_ward(self):
        """Devout Ward always activates; archetype_used_name is 'devout'."""
        c1 = make_card("c1")
        friendly = make_card("friendly")
        board: list[BoardCell | None] = [None] * 9
        board[5] = BoardCell(card_key="friendly", owner=0)
        state = make_state(
            board=board,
            p0_hand=["c1"],
            p0_archetype=Archetype.DEVOUT,
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0, card_key="c1", cell_index=0, use_archetype=True,
            devout_ward_cell=5,
        )
        rng = Random(42)
        result = apply_intent(state, intent, {**_card_lookup(c1), "friendly": friendly}, rng=rng)
        assert result.last_move is not None
        assert result.last_move.archetype_used_name == "devout"
        assert result.last_move.warded_cell == 5


class TestIntimidateTargetCell:
    def test_intimidate_target_cell_set(self):
        c1 = make_card("c1", n=5, e=5, s=5, w=5)
        c2 = make_card("c2", n=3, e=3, s=3, w=3)
        board = [None] * 9
        board[1] = BoardCell(card_key="c2", owner=1)
        state = make_state(
            board=board,
            p0_hand=["c1"],
            p0_archetype=Archetype.INTIMIDATE,
            p1_hand=["c2"],
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="c1",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        result = apply_intent(state, intent, _card_lookup(c1, c2), rng=Random(42))
        assert result.last_move is not None
        assert result.last_move.intimidate_target_cell == 1

    def test_intimidate_target_cell_null_without_archetype(self):
        c1 = make_card("c1")
        state = make_state(
            p0_hand=["c1"],
            p0_archetype=Archetype.SKULKER,
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0, card_key="c1", cell_index=0, use_archetype=False
        )
        result = apply_intent(state, intent, _card_lookup(c1), rng=Random(42))
        assert result.last_move is not None
        assert result.last_move.intimidate_target_cell is None

    def test_non_intimidate_archetype_has_null_target_cell(self):
        c1 = make_card("c1")
        state = make_state(
            p0_hand=["c1"],
            p0_archetype=Archetype.SKULKER,
            current_player_index=0,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="c1",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="n",
        )
        result = apply_intent(state, intent, _card_lookup(c1), rng=Random(42))
        assert result.last_move is not None
        assert result.last_move.intimidate_target_cell is None


class TestLastMoveInfoFields:
    def test_archetype_used_name_defaults_to_none(self):
        lm = LastMoveInfo(
            player_index=0, card_key="c1", cell_index=0, mists_roll=3, mists_effect="none"
        )
        assert lm.archetype_used_name is None
        assert lm.intimidate_target_cell is None

    def test_archetype_used_name_roundtrip(self):
        lm = LastMoveInfo(
            player_index=0, card_key="c1", cell_index=0, mists_roll=3, mists_effect="none",
            archetype_used_name="martial", intimidate_target_cell=5,
        )
        data = lm.model_dump()
        restored = LastMoveInfo.model_validate(data)
        assert restored.archetype_used_name == "martial"
        assert restored.intimidate_target_cell == 5
