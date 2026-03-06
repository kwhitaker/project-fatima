"""Tests for US-PR-004: AI archetype selection with hand-aware heuristic.

Covers:
- Easy AI picks randomly (distribution check over multiple seeds)
- Medium+ AI picks Skulker for weak-adjacent-strong hands
- Medium+ AI picks Caster for mid-range hands
- Medium+ AI picks Devout for hands with one standout card
- Medium+ AI picks Intimidate for moderate-attack hands
- Medium+ AI picks Martial for clustered-strong hands
"""

from collections import Counter
from random import Random

import pytest

from app.models.cards import CardDefinition, CardSides
from app.models.game import AIDifficulty, Archetype
from app.services.game_service import _ai_auto_archetype
from tests.conftest import make_card


def _hand(specs: list[tuple[int, int, int, int]]) -> list[CardDefinition]:
    """Build a 5-card hand from (n, e, s, w) tuples."""
    return [make_card(f"h{i}", n=s[0], e=s[1], s=s[2], w=s[3]) for i, s in enumerate(specs)]


class TestEasyRandomDistribution:
    """Easy AI should pick randomly from all 5 archetypes."""

    def test_easy_picks_all_archetypes_over_many_seeds(self) -> None:
        hand = [make_card(f"c{i}") for i in range(5)]  # uniform 5/5/5/5
        picks: Counter[Archetype] = Counter()
        for seed in range(200):
            picks[_ai_auto_archetype(hand, AIDifficulty.EASY, Random(seed))] += 1
        # All 5 archetypes should appear at least once in 200 trials
        assert set(picks.keys()) == set(Archetype), f"Missing archetypes: {set(Archetype) - set(picks.keys())}"


class TestMediumHandAwareSelection:
    """Medium+ AI should score archetypes against hand composition."""

    def test_skulker_for_weak_adjacent_strong(self) -> None:
        """Hand with cards having weak side adjacent to strong side → Skulker."""
        # Cards with pattern: one weak side (≤3) adjacent to one strong side (≥7)
        hand = _hand([
            (2, 8, 5, 5),  # N=2 weak, E=8 strong, adjacent
            (3, 7, 4, 5),  # N=3 weak, E=7 strong, adjacent
            (1, 9, 4, 4),
            (2, 8, 3, 5),
            (3, 7, 5, 4),
        ])
        result = _ai_auto_archetype(hand, AIDifficulty.MEDIUM, Random(42))
        assert result == Archetype.SKULKER

    def test_caster_for_mid_range_hands(self) -> None:
        """Hand with many mid-range sides (5-7) → Caster (benefits most from +2)."""
        hand = _hand([
            (6, 6, 6, 6),
            (5, 7, 5, 7),
            (6, 5, 7, 6),
            (7, 6, 5, 6),
            (5, 6, 7, 5),
        ])
        result = _ai_auto_archetype(hand, AIDifficulty.MEDIUM, Random(42))
        assert result == Archetype.CASTER

    def test_devout_for_one_standout_card(self) -> None:
        """Hand with one high-value card worth protecting → Devout."""
        hand = _hand([
            (9, 9, 9, 3),  # standout card — very high average
            (3, 3, 3, 3),
            (3, 3, 3, 3),
            (3, 3, 3, 3),
            (3, 3, 3, 3),
        ])
        result = _ai_auto_archetype(hand, AIDifficulty.MEDIUM, Random(42))
        assert result == Archetype.DEVOUT

    def test_intimidate_for_moderate_plus_weak_sides(self) -> None:
        """Hand mixing moderate (5-7) and weak (3-4) sides → Intimidate."""
        # Intimidate shines when you have moderate sides that need just a small edge,
        # plus weak sides that benefit from -3 debuff on opponent
        hand = _hand([
            (6, 4, 6, 3),
            (5, 3, 5, 4),
            (6, 4, 5, 3),
            (5, 3, 6, 4),
            (6, 4, 5, 3),
        ])
        result = _ai_auto_archetype(hand, AIDifficulty.MEDIUM, Random(42))
        assert result == Archetype.INTIMIDATE

    def test_martial_for_clustered_strong(self) -> None:
        """Hand with strong sides clustered together → Martial (rotation unlocks them)."""
        # Strong sides adjacent to each other, moderate-weak sides adjacent.
        # No ≤3 adjacent to ≥7 pattern (that would favor Skulker).
        hand = _hand([
            (8, 8, 4, 4),  # strong N+E clustered, weak S+W clustered
            (7, 8, 4, 4),
            (8, 7, 4, 4),
            (7, 7, 4, 4),
            (8, 8, 4, 4),
        ])
        result = _ai_auto_archetype(hand, AIDifficulty.MEDIUM, Random(42))
        assert result == Archetype.MARTIAL


class TestHardNightmareUsesSameScoring:
    """Hard and Nightmare should also use hand-aware scoring (not random)."""

    @pytest.mark.parametrize("difficulty", [AIDifficulty.HARD, AIDifficulty.NIGHTMARE])
    def test_hard_nightmare_picks_skulker_for_skulker_hand(self, difficulty: AIDifficulty) -> None:
        hand = _hand([
            (2, 8, 5, 5),
            (3, 7, 4, 5),
            (1, 9, 4, 4),
            (2, 8, 3, 5),
            (3, 7, 5, 4),
        ])
        result = _ai_auto_archetype(hand, difficulty, Random(42))
        assert result == Archetype.SKULKER
