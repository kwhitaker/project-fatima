"""Game orchestration: create, join, archetype selection, and move submission."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from random import Random

from app.models.cards import CardDefinition
from app.models.game import AIDifficulty, Archetype, GameResult, GameState, GameStatus, PlayerState

AI_PLAYER_ID = "00000000-0000-0000-0000-000000000001"

AI_DISPLAY_NAMES: dict[AIDifficulty, str] = {
    AIDifficulty.EASY: "Ireena Kolyana",
    AIDifficulty.MEDIUM: "Rahadin",
    AIDifficulty.HARD: "Strahd von Zarovich",
    AIDifficulty.NIGHTMARE: "The Dark Powers",
}
from app.rules.deck import HAND_SIZE, generate_matched_deals
from app.rules.errors import ArchetypeNotSelectedError
from app.rules.reducer import PlacementIntent, apply_intent
from app.store import CardStore, ConflictError, GameStore


class ActiveGameExistsError(Exception):
    """Raised when a player tries to create/join but already has a non-complete game."""

    def __init__(self, existing_game_id: str) -> None:
        self.existing_game_id = existing_game_id
        super().__init__(
            f"You already have a non-complete game ({existing_game_id}). "
            "Finish or forfeit it before starting a new one."
        )


def _check_no_active_game(game_store: GameStore, player_id: str) -> None:
    """Raise ActiveGameExistsError if player has any non-complete game."""
    games = game_store.list_games_for_player(player_id)
    for g in games:
        if g.status != GameStatus.COMPLETE:
            raise ActiveGameExistsError(g.game_id)


def _ai_auto_draft(
    deal: list[CardDefinition],
    difficulty: AIDifficulty,
    rng: Random,
) -> list[str]:
    """Pick HAND_SIZE cards from the AI's deal based on difficulty strategy."""
    if difficulty == AIDifficulty.EASY:
        picked = rng.sample(deal, HAND_SIZE)
        return [c.card_key for c in picked]
    elif difficulty == AIDifficulty.MEDIUM:
        # Pick 5 with highest total side values
        def _total(c: CardDefinition) -> int:
            return c.sides.n + c.sides.e + c.sides.s + c.sides.w

        sorted_deal = sorted(deal, key=_total, reverse=True)
        return [c.card_key for c in sorted_deal[:HAND_SIZE]]
    else:
        # Hard/Nightmare: best defensive+offensive coverage (highest min-side sum)
        def _coverage(c: CardDefinition) -> int:
            s = c.sides
            return min(s.n, s.e, s.s, s.w) + s.n + s.e + s.s + s.w

        sorted_deal = sorted(deal, key=_coverage, reverse=True)
        return [c.card_key for c in sorted_deal[:HAND_SIZE]]


def _score_skulker(hand: list[CardDefinition]) -> float:
    """Skulker scores high when hand has cards with a weak side adjacent to a strong side."""
    score = 0.0
    for card in hand:
        sides = [card.sides.n, card.sides.e, card.sides.s, card.sides.w]
        for i in range(4):
            adj = sides[(i + 1) % 4]
            if sides[i] <= 3 and adj >= 7:
                score += (adj - sides[i])  # bigger gap = more Skulker value
            if adj <= 3 and sides[i] >= 7:
                score += (sides[i] - adj)
    return score


def _score_martial(hand: list[CardDefinition]) -> float:
    """Martial scores high when strong sides are clustered (rotation unlocks value)."""
    score = 0.0
    for card in hand:
        sides = [card.sides.n, card.sides.e, card.sides.s, card.sides.w]
        # Count how many strong sides (≥7) are adjacent to each other
        strong = [s >= 7 for s in sides]
        cluster_count = sum(1 for i in range(4) if strong[i] and strong[(i + 1) % 4])
        # Also reward when weak sides (≤4) are adjacent (rotation moves them together)
        weak = [s <= 4 for s in sides]
        weak_cluster = sum(1 for i in range(4) if weak[i] and weak[(i + 1) % 4])
        # Cards with clustered strong AND clustered weak benefit most from rotation
        if cluster_count > 0 and weak_cluster > 0:
            score += cluster_count * 4 + weak_cluster * 3
        elif cluster_count > 0:
            score += cluster_count * 3
    return score


def _score_caster(hand: list[CardDefinition]) -> float:
    """Caster scores high when hand has many mid-range sides (5-7) that benefit from +2.

    Caster gives +2 to ALL sides, so hands where most sides are mid-range
    get the biggest overall lift. Penalize hands with many weak sides (≤3)
    since even +2 only brings them to 5 max.
    """
    mid_count = 0
    weak_count = 0
    for card in hand:
        for s in [card.sides.n, card.sides.e, card.sides.s, card.sides.w]:
            if 5 <= s <= 7:
                mid_count += 1
            elif s <= 3:
                weak_count += 1
    # Reward density of mid-range sides; penalize weak sides
    return mid_count * 1.5 - weak_count * 0.5


def _score_devout(hand: list[CardDefinition]) -> float:
    """Devout scores high when hand has one standout high-value card worth protecting."""
    if not hand:
        return 0.0
    averages = [
        (card.sides.n + card.sides.e + card.sides.s + card.sides.w) / 4.0
        for card in hand
    ]
    best = max(averages)
    rest_avg = sum(a for a in averages if a != best) / max(len(averages) - 1, 1)
    # Score based on gap between best card and rest of hand
    gap = best - rest_avg
    return gap * 5 if gap > 1.5 else gap


def _score_intimidate(hand: list[CardDefinition]) -> float:
    """Intimidate scores high when hand has moderate attacking sides (5-7).

    A -3 debuff turns opponent's 7→4 or 8→5, letting moderate sides win.
    Best for hands mixing moderate and weak (≤3) sides.
    """
    moderate_count = 0
    weak_count = 0
    for card in hand:
        for s in [card.sides.n, card.sides.e, card.sides.s, card.sides.w]:
            if 5 <= s <= 7:
                moderate_count += 1
            elif s <= 3:
                weak_count += 1
    # Intimidate shines when you have moderate sides AND weak (≤3) sides
    if weak_count >= 4:
        return moderate_count * 1.2 + weak_count * 0.8
    return moderate_count * 1.0


def _ai_auto_archetype(
    hand: list[CardDefinition],
    difficulty: AIDifficulty,
    rng: Random,
) -> Archetype:
    """Pick an archetype for the AI based on difficulty and hand composition."""
    if difficulty == AIDifficulty.EASY:
        return rng.choice(list(Archetype))

    # Score each archetype against the hand
    scores: dict[Archetype, float] = {
        Archetype.SKULKER: _score_skulker(hand),
        Archetype.MARTIAL: _score_martial(hand),
        Archetype.CASTER: _score_caster(hand),
        Archetype.DEVOUT: _score_devout(hand),
        Archetype.INTIMIDATE: _score_intimidate(hand),
    }

    best_score = max(scores.values())
    # Break ties randomly
    best = [a for a, s in scores.items() if s == best_score]
    return rng.choice(best)


def create_game_vs_ai(
    game_store: GameStore,
    card_store: CardStore,
    player_id: str,
    email: str | None,
    difficulty: AIDifficulty,
    seed: int | None = None,
) -> GameState:
    """Create a new single-player game against an AI opponent.

    The AI auto-drafts and auto-selects archetype. The human player still
    needs to draft and pick archetype.
    """
    _check_no_active_game(game_store, player_id)
    game_id = str(uuid.uuid4())
    if seed is None:
        seed = Random().randint(0, 2**31 - 1)

    rng = Random(seed)

    # Generate deals
    cards = card_store.list_cards()
    deal_a, deal_b = generate_matched_deals(cards, seed=seed)

    # Build card lookup for AI draft
    card_lookup = {c.card_key: c for c in cards}

    # AI auto-draft
    ai_hand_keys = _ai_auto_draft(deal_b, difficulty, rng)
    ai_hand_cards = [card_lookup[k] for k in ai_hand_keys]

    # AI auto-archetype
    ai_archetype = _ai_auto_archetype(ai_hand_cards, difficulty, rng)

    # Pick starting player deterministically
    starting = Random(seed).randint(0, 1)

    # Generate board elements
    board_elements = Random(seed).choices(
        ["blood", "holy", "arcane", "shadow", "nature"], k=9
    )

    human_player = PlayerState(
        player_id=player_id,
        email=email,
        deal=[c.card_key for c in deal_a],
    )
    ai_player = PlayerState(
        player_id=AI_PLAYER_ID,
        email=AI_DISPLAY_NAMES[difficulty],
        player_type="ai",
        ai_difficulty=difficulty,
        hand=ai_hand_keys,
        deal=[],
        archetype=ai_archetype,
    )

    initial_state = GameState(
        game_id=game_id,
        seed=seed,
        status=GameStatus.DRAFTING,
        players=[human_player, ai_player],
        starting_player_index=starting,
        current_player_index=starting,
        board_elements=board_elements,
        created_at=datetime.now(UTC).isoformat(),
    )
    game_store.create_game(game_id, initial_state)
    return initial_state


def create_game(
    game_store: GameStore,
    card_store: CardStore,
    player_id: str,
    seed: int | None = None,
    email: str | None = None,
) -> GameState:
    """Create a new game and auto-join the caller as player 1."""
    _check_no_active_game(game_store, player_id)
    game_id = str(uuid.uuid4())
    if seed is None:
        seed = Random().randint(0, 2**31 - 1)
    initial_state = GameState(
        game_id=game_id,
        seed=seed,
        status=GameStatus.WAITING,
        players=[PlayerState(player_id=player_id, email=email)],
        created_at=datetime.now(UTC).isoformat(),
    )
    game_store.create_game(game_id, initial_state)
    return initial_state


def join_game(
    game_store: GameStore,
    card_store: CardStore,
    game_id: str,
    player_id: str,
    email: str | None = None,
) -> GameState:
    _check_no_active_game(game_store, player_id)
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    if state.status != GameStatus.WAITING:
        raise ValueError("Game is not in WAITING state")
    if any(p.player_id == player_id for p in state.players):
        raise ValueError(f"Player {player_id!r} already joined")
    if len(state.players) >= 2:
        raise ValueError("Game already has 2 players")

    new_players = list(state.players) + [PlayerState(player_id=player_id, email=email)]

    extra_updates: dict[str, object] = {}
    if len(new_players) == 2:
        cards = card_store.list_cards()
        deal_a, deal_b = generate_matched_deals(cards, seed=state.seed)
        new_players[0] = new_players[0].model_copy(update={"deal": [c.card_key for c in deal_a]})
        new_players[1] = new_players[1].model_copy(update={"deal": [c.card_key for c in deal_b]})
        new_status = GameStatus.DRAFTING
        # Pick starting player deterministically from seed
        starting = Random(state.seed).randint(0, 1)
        extra_updates["starting_player_index"] = starting
        extra_updates["current_player_index"] = starting
        # Generate board elements deterministically from seed (one per cell)
        extra_updates["board_elements"] = Random(state.seed).choices(
            ["blood", "holy", "arcane", "shadow", "nature"], k=9
        )
    else:
        new_status = state.status

    new_state = state.model_copy(
        update={
            "players": new_players,
            "status": new_status,
            "state_version": state.state_version + 1,
            **extra_updates,
        }
    )
    game_store.append_event(
        game_id=game_id,
        event_type="player_joined",
        payload={"player_id": player_id},
        expected_version=state.state_version,
        new_state=new_state,
    )
    return new_state


def submit_draft(
    game_store: GameStore,
    game_id: str,
    player_id: str,
    selected_cards: list[str],
) -> GameState:
    """Submit a player's draft selection (pick HAND_SIZE cards from their deal)."""
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    if state.status != GameStatus.DRAFTING:
        raise ValueError("Game is not in DRAFTING state")

    player_index = next(
        (i for i, p in enumerate(state.players) if p.player_id == player_id), None
    )
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")

    player = state.players[player_index]
    if not player.deal:
        raise ValueError(f"Player {player_id!r} has already submitted their draft")

    if len(selected_cards) != HAND_SIZE:
        raise ValueError(
            f"Must select exactly {HAND_SIZE} cards; got {len(selected_cards)}"
        )

    # Validate all selected cards are in the deal
    deal_set = set(player.deal)
    for card_key in selected_cards:
        if card_key not in deal_set:
            raise ValueError(f"Card {card_key!r} is not in your deal")

    # Check for duplicates in selection
    if len(set(selected_cards)) != len(selected_cards):
        raise ValueError("Duplicate cards in selection")

    new_players = list(state.players)
    new_players[player_index] = player.model_copy(
        update={"hand": selected_cards, "deal": []}
    )

    # If both players have now drafted, transition to ACTIVE
    both_drafted = all(
        len(p.hand) == HAND_SIZE and len(p.deal) == 0 for p in new_players
    )
    new_status = GameStatus.ACTIVE if both_drafted else state.status

    new_state = state.model_copy(
        update={
            "players": new_players,
            "status": new_status,
            "state_version": state.state_version + 1,
        }
    )
    game_store.append_event(
        game_id=game_id,
        event_type="draft_submitted",
        payload={"player_id": player_id},
        expected_version=state.state_version,
        new_state=new_state,
    )
    return new_state


def select_archetype(
    game_store: GameStore, game_id: str, player_id: str, archetype: Archetype
) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")
    player = state.players[player_index]
    if player.archetype is not None:
        raise ValueError(f"Player {player_id!r} has already selected an archetype")

    new_players = list(state.players)
    new_players[player_index] = player.model_copy(update={"archetype": archetype})
    new_state = state.model_copy(
        update={
            "players": new_players,
            "state_version": state.state_version + 1,
        }
    )
    game_store.append_event(
        game_id=game_id,
        event_type="archetype_selected",
        payload={"player_id": player_id, "archetype": archetype.value},
        expected_version=state.state_version,
        new_state=new_state,
    )
    return new_state


def leave_game(
    game_store: GameStore,
    game_id: str,
    player_id: str,
    state_version: int,
    idempotency_key: str | None = None,
) -> GameState | None:
    """Leave a game.

    ACTIVE + 2 players → forfeit: append game_forfeited event, other player wins.
    WAITING + 1 player → delete the game lobby.
    Returns the new GameState for forfeits, or None when the game was deleted.
    """
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")

    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")

    if state.status in (GameStatus.ACTIVE, GameStatus.DRAFTING):
        other_index = 1 - player_index
        new_result = GameResult(
            winner=other_index,
            is_draw=False,
            completion_reason="forfeit",
            forfeit_by_index=player_index,
        )
        new_state = state.model_copy(
            update={
                "status": GameStatus.COMPLETE,
                "result": new_result,
                "state_version": state.state_version + 1,
            }
        )
        game_store.append_event(
            game_id=game_id,
            event_type="game_forfeited",
            payload={
                "forfeit_by": player_id,
                "winner": state.players[other_index].player_id,
            },
            expected_version=state_version,
            new_state=new_state,
            idempotency_key=idempotency_key,
        )
        return new_state
    elif state.status == GameStatus.WAITING and len(state.players) == 1:
        game_store.delete_game(game_id, expected_version=state_version)
        return None
    else:
        raise ValueError(
            f"Cannot leave game {game_id!r}: "
            f"status={state.status.value!r}, players={len(state.players)}"
        )


def submit_move(
    game_store: GameStore,
    card_store: CardStore,
    game_id: str,
    player_id: str,
    card_key: str,
    cell_index: int,
    expected_version: int,
    use_archetype: bool = False,
    skulker_boost_side: str | None = None,
    intimidate_target_cell: int | None = None,
    martial_rotation_direction: str | None = None,
    idempotency_key: str | None = None,
) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")
    if state.state_version != expected_version:
        raise ConflictError(
            f"Version conflict for game {game_id!r}: "
            f"expected {expected_version}, got {state.state_version}"
        )

    player = state.players[player_index]
    if player.archetype is None:
        raise ArchetypeNotSelectedError(
            "You must select an archetype before placing cards. "
            "Use POST /games/{game_id}/archetype to select one."
        )

    card_lookup = {c.card_key: c for c in card_store.list_cards()}
    # Derive per-move RNG from seed + current state_version for deterministic replay
    rng = Random(state.seed + state.state_version)

    intent = PlacementIntent(
        player_index=player_index,
        card_key=card_key,
        cell_index=cell_index,
        use_archetype=use_archetype,
        skulker_boost_side=skulker_boost_side,
        intimidate_target_cell=intimidate_target_cell,
        martial_rotation_direction=martial_rotation_direction,
    )
    new_state = apply_intent(state, intent, card_lookup, rng)

    game_store.append_event(
        game_id=game_id,
        event_type="card_placed",
        payload={"player_id": player_id, "card_key": card_key, "cell_index": cell_index},
        expected_version=expected_version,
        new_state=new_state,
        idempotency_key=idempotency_key,
    )

    # Attach AI reaction comment after a human move in an AI game
    if player.player_type == "human":
        attach_human_move_reaction(state, new_state, game_store)
        # Re-read state in case a comment was attached
        updated = game_store.get_game(game_id)
        if updated is not None:
            return updated

    return new_state


# ---------------------------------------------------------------------------
# AI turn delay ranges per difficulty (seconds)
# ---------------------------------------------------------------------------
_AI_DELAY_RANGES: dict[AIDifficulty, tuple[float, float]] = {
    AIDifficulty.EASY: (0.3, 0.8),
    AIDifficulty.MEDIUM: (0.5, 1.0),
    AIDifficulty.HARD: (0.8, 1.5),
    AIDifficulty.NIGHTMARE: (1.5, 2.5),
}

logger = logging.getLogger(__name__)


def _attach_ai_comment_after_move(
    state_before: GameState,
    state_after: GameState,
    ai_index: int,
    game_store: GameStore,
) -> None:
    """Evaluate AI comment triggers after a move and attach to last_move if triggered."""
    from app.rules.ai_comments import detect_ai_move_triggers, evaluate_ai_comment

    if state_after.last_move is None:
        return

    triggers = detect_ai_move_triggers(state_before, state_after, ai_index)
    if not triggers:
        return

    comment_rng = Random(state_after.seed + state_after.state_version + 9999)
    comment = evaluate_ai_comment(state_after, ai_index, triggers, comment_rng)
    if comment is None:
        return

    # Update last_move with comment
    updated_last_move = state_after.last_move.model_copy(update={"ai_comment": comment})
    updated_state = state_after.model_copy(update={"last_move": updated_last_move})
    game_store.update_state(state_after.game_id, updated_state)


def attach_human_move_reaction(
    state_before: GameState,
    state_after: GameState,
    game_store: GameStore,
) -> None:
    """After a human move in an AI game, evaluate AI reaction triggers.

    If the opponent is AI, detect triggers (ai_got_captured, etc.) and attach
    an ai_comment to the human's last_move.
    """
    from app.rules.ai_comments import detect_human_move_triggers, evaluate_ai_comment

    if state_after.last_move is None:
        return

    # Find the AI player
    ai_index: int | None = None
    for i, p in enumerate(state_after.players):
        if p.player_type == "ai":
            ai_index = i
            break
    if ai_index is None:
        return

    human_index = state_after.last_move.player_index
    if human_index == ai_index:
        return  # This was the AI's move, not the human's

    triggers = detect_human_move_triggers(state_before, state_after, ai_index)
    if not triggers:
        return

    comment_rng = Random(state_after.seed + state_after.state_version + 8888)
    comment = evaluate_ai_comment(state_after, ai_index, triggers, comment_rng)
    if comment is None:
        return

    updated_last_move = state_after.last_move.model_copy(update={"ai_comment": comment})
    updated_state = state_after.model_copy(update={"last_move": updated_last_move})
    game_store.update_state(state_after.game_id, updated_state)


def is_ai_turn(state: GameState) -> bool:
    """Return True if the current turn belongs to an AI player and the game is ACTIVE.

    Also returns False if any player has not yet selected an archetype,
    to prevent the AI from moving before the human finishes setup.
    """
    if state.status != GameStatus.ACTIVE:
        return False
    if any(p.archetype is None for p in state.players):
        return False
    current = state.players[state.current_player_index]
    return current.player_type == "ai"


async def execute_ai_turn(
    game_id: str,
    game_store: GameStore,
    card_store: CardStore,
) -> None:
    """Load game state, compute AI move, and submit it.

    Called as a background task after a human move or draft transition.
    """
    from app.rules.ai import choose_move

    state = game_store.get_game(game_id)
    if state is None:
        return
    if state.status != GameStatus.ACTIVE:
        return

    ai_index = state.current_player_index
    ai_player = state.players[ai_index]
    if ai_player.player_type != "ai":
        return

    difficulty = ai_player.ai_difficulty
    if difficulty is None:
        return

    # Delay before AI moves (randomized from seed for determinism)
    delay_rng = Random(state.seed + state.state_version + 1000)
    lo, hi = _AI_DELAY_RANGES[difficulty]
    delay = delay_rng.uniform(lo, hi)
    await asyncio.sleep(delay)

    # Re-fetch state after delay to check it's still valid
    state = game_store.get_game(game_id)
    if state is None or state.status != GameStatus.ACTIVE:
        return
    if state.players[state.current_player_index].player_type != "ai":
        return

    card_lookup = {c.card_key: c for c in card_store.list_cards()}
    move_rng = Random(state.seed + state.state_version)

    # Nightmare (MCTS): acquire semaphore, run compute in executor to avoid blocking
    if difficulty == AIDifficulty.NIGHTMARE:
        from app.rules.mcts import _nightmare_semaphore, acquire_nightmare_semaphore

        try:
            await asyncio.wait_for(acquire_nightmare_semaphore(), timeout=10.0)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning(
                "Nightmare AI semaphore timeout for game %s — The Dark Powers are occupied",
                game_id,
            )
            return
        try:
            loop = asyncio.get_event_loop()
            intent = await loop.run_in_executor(
                None, choose_move, state, ai_index, difficulty, card_lookup, move_rng
            )
        finally:
            _nightmare_semaphore.release()
    elif difficulty == AIDifficulty.HARD:
        # Hard (Expectimax): run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        intent = await loop.run_in_executor(
            None, choose_move, state, ai_index, difficulty, card_lookup, move_rng
        )
    else:
        intent = choose_move(state, ai_index, difficulty, card_lookup, move_rng)

    try:
        new_state = submit_move(
            game_store=game_store,
            card_store=card_store,
            game_id=game_id,
            player_id=ai_player.player_id,
            card_key=intent.card_key,
            cell_index=intent.cell_index,
            expected_version=state.state_version,
            use_archetype=intent.use_archetype,
            skulker_boost_side=intent.skulker_boost_side,
            intimidate_target_cell=intent.intimidate_target_cell,
            martial_rotation_direction=intent.martial_rotation_direction,
        )
    except Exception:
        logger.exception("AI turn failed for game %s", game_id)
        return

    # Attach AI commentary after successful move
    _attach_ai_comment_after_move(state, new_state, ai_index, game_store)
