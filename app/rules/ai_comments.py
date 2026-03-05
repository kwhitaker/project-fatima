"""AI commentary system: in-character comments per difficulty/character.

Each AI character has comment pools keyed by trigger condition. After a move,
``evaluate_ai_comment`` checks triggers and returns a comment string (or None).
Comment chance is 30-50% per trigger (rolled from game RNG).
"""

from random import Random

from app.models.game import AIDifficulty, GameState

# ---------------------------------------------------------------------------
# Comment pools per character per trigger
# ---------------------------------------------------------------------------

_IREENA_COMMENTS: dict[str, list[str]] = {
    "ai_captured_cards": [
        "Oh, clever move!",
        "I think I'm getting the hang of this!",
        "Did I just do that? I did!",
        "Father would be proud!",
        "I'm learning!",
        "Ha! Take that!",
        "Is that how you do it?",
        "That felt right!",
        "I surprised myself!",
        "Beginner's luck, maybe?",
    ],
    "ai_got_captured": [
        "Wait, that was mine!",
        "Oh no, how did you do that?",
        "I didn't see that coming...",
        "You're really good at this!",
        "That's not fair! ...is it?",
        "I'll get you back for that!",
        "Oops! I left that open, didn't I?",
        "You must teach me your ways!",
        "Well played, I suppose...",
        "I'm still learning!",
    ],
    "plus_triggered": [
        "What just happened?!",
        "Everything changed at once!",
        "Is that a special move?",
        "Oh! Multiple cards!",
        "That was unexpected!",
    ],
    "elemental_triggered": [
        "The elements are helping!",
        "I feel a connection to this place!",
        "Nature is on my side!",
        "The magic tingles!",
        "Something mystical happened!",
    ],
    "archetype_used": [
        "I have a trick too!",
        "Father taught me this one!",
        "Let me try something...",
        "Was that right? I think so!",
        "Special move!",
    ],
    "game_ending": [
        "What a fun game!",
        "Can we play again?",
        "That was exciting!",
        "I had such a good time!",
        "Thank you for playing with me!",
    ],
    "game_won": [
        "I won? I actually won!",
        "I can't believe it — I did it!",
        "Father would be so proud!",
        "That was my first real victory!",
        "I'm getting better at this!",
    ],
    "game_lost": [
        "You were wonderful!",
        "I had fun even though I lost!",
        "You'll have to teach me your secrets!",
        "Next time I'll do better, I promise!",
        "That was a great game, thank you!",
    ],
}

_RAHADIN_COMMENTS: dict[str, list[str]] = {
    "ai_captured_cards": [
        "Predictable.",
        "Efficient.",
        "As expected.",
        "You leave yourself open.",
        "A calculated outcome.",
        "Precision yields results.",
        "Another one falls.",
        "Methodical.",
        "Your defenses crumble.",
        "Order prevails.",
    ],
    "ai_got_captured": [
        "You waste my time.",
        "An inconvenience.",
        "That will not happen again.",
        "A temporary setback.",
        "Noted.",
        "I underestimated your desperation.",
        "Enjoy this small victory.",
        "You have my attention now.",
        "A miscalculation. It won't recur.",
        "Irrelevant in the larger scheme.",
    ],
    "plus_triggered": [
        "A chain of inevitability.",
        "Multiple targets neutralized.",
        "Systematic elimination.",
        "The dominoes fall.",
        "Coordinated precision.",
    ],
    "elemental_triggered": [
        "The elements obey order.",
        "Natural advantage, exploited.",
        "Even nature serves a purpose.",
        "Elemental alignment: optimal.",
        "The environment is a tool.",
    ],
    "archetype_used": [
        "A technique perfected through service.",
        "Lord Strahd taught me this.",
        "Observe carefully. You won't see it again.",
        "Centuries of practice.",
        "A refined approach.",
    ],
    "game_ending": [
        "This concludes our business.",
        "As I anticipated from the start.",
        "Your performance was... adequate.",
        "The outcome was never in doubt.",
        "Report to Lord Strahd: task complete.",
    ],
    "game_won": [
        "The outcome was never in question.",
        "Dismissed.",
        "Another task completed for Lord Strahd.",
        "Efficiency. Nothing more.",
        "You were outmatched from the start.",
    ],
    "game_lost": [
        "...Noted.",
        "This changes nothing.",
        "A statistical anomaly. Nothing more.",
        "I will not forget this.",
        "Lord Strahd will hear of this. Not from me.",
    ],
}

_STRAHD_COMMENTS: dict[str, list[str]] = {
    "ai_captured_cards": [
        "You amuse me, mortal.",
        "Your struggle is... entertaining.",
        "Did you truly believe that would work?",
        "I have played this game for centuries.",
        "Another soul claimed.",
        "The night takes what it will.",
        "Resistance is a quaint notion.",
        "You cannot outplay eternity.",
        "How delightfully futile.",
        "Barovia always wins.",
    ],
    "ai_got_captured": [
        "Bold. Foolish, but bold.",
        "You dare?",
        "A spark of defiance. How refreshing.",
        "Enjoy this moment. It will not last.",
        "You have earned my ire.",
        "That was... unexpected. It won't happen again.",
        "Even the mouse bites. Once.",
        "I allowed that. Remember it.",
        "Your courage will be your undoing.",
        "A pyrrhic victory at best.",
    ],
    "plus_triggered": [
        "The board bends to my will.",
        "A cascade of darkness.",
        "All things fall before me.",
        "Watch closely — this is mastery.",
        "The pieces align as I command.",
    ],
    "elemental_triggered": [
        "The very land serves me.",
        "Barovia's power flows through my cards.",
        "Nature recognizes its master.",
        "The elements kneel.",
        "My domain empowers me.",
    ],
    "archetype_used": [
        "Behold the power of Barovia's lord.",
        "A taste of true darkness.",
        "I have abilities you cannot comprehend.",
        "Centuries of conquest, distilled.",
        "This is but a fraction of my power.",
    ],
    "game_ending": [
        "The game ends as it must.",
        "All who enter Barovia meet this fate.",
        "Come back when you've learned something.",
        "I expected more. Perhaps next time.",
        "The lord of Barovia does not lose.",
    ],
    "game_won": [
        "Kneel.",
        "Did you expect anything less?",
        "All who challenge me meet this fate.",
        "I am the land. The land never loses.",
        "Your defeat was written before you were born.",
    ],
    "game_lost": [
        "Enjoy this. It will not happen again.",
        "A momentary lapse. Nothing more.",
        "You have made a powerful enemy today.",
        "This changes nothing about your fate.",
        "I let you win. Remember that.",
    ],
}

_DARK_POWERS_COMMENTS: dict[str, list[str]] = {
    "ai_captured_cards": [
        "The mists remember what you have forgotten.",
        "Every choice narrows the path.",
        "We have seen this ending before.",
        "Your cards were never truly yours.",
        "The pattern completes itself.",
        "All threads lead to us.",
        "You play, but we have already won.",
        "Inevitable.",
        "The void claims another.",
        "This was written long ago.",
    ],
    "ai_got_captured": [
        "An echo of a choice already made.",
        "You believe you chose this. You didn't.",
        "Even resistance serves our purpose.",
        "Interesting. The pattern shifts.",
        "A deviation. Temporary.",
        "You move, but the board remains ours.",
        "Free will is the grandest illusion.",
        "That move existed before you made it.",
        "The mists allow it. For now.",
        "A ripple in an ocean of fate.",
    ],
    "plus_triggered": [
        "All things are connected in the dark.",
        "The web tightens.",
        "Resonance. The pattern reinforces.",
        "Threads converge.",
        "What touches one, touches all.",
    ],
    "elemental_triggered": [
        "The elements are merely our instruments.",
        "Reality bends at our whim.",
        "The veil thins where power gathers.",
        "Cosmic alignment favors the inevitable.",
        "The fabric of the world obeys.",
    ],
    "archetype_used": [
        "We move through vessels.",
        "A gift from beyond the mists.",
        "The dark grants. The dark takes.",
        "Power borrowed is power owed.",
        "An echo of something ancient stirs.",
    ],
    "game_ending": [
        "The game ends. The game begins again.",
        "You will return. They always do.",
        "We are patient beyond measure.",
        "This ending was the only one.",
        "The mists part. For now.",
    ],
    "game_won": [
        "As it was always meant to be.",
        "The pattern completes. Again.",
        "You were never meant to win this.",
        "All roads led here. All roads lead here.",
        "The dark is patient. The dark prevails.",
    ],
    "game_lost": [
        "This outcome changes nothing.",
        "A thread unravels. The tapestry holds.",
        "You believe you won. How quaint.",
        "We have already forgotten this moment.",
        "Victory is an illusion we permit.",
    ],
}

_COMMENT_POOLS: dict[AIDifficulty, dict[str, list[str]]] = {
    AIDifficulty.EASY: _IREENA_COMMENTS,
    AIDifficulty.MEDIUM: _RAHADIN_COMMENTS,
    AIDifficulty.HARD: _STRAHD_COMMENTS,
    AIDifficulty.NIGHTMARE: _DARK_POWERS_COMMENTS,
}

# Trigger chance range: 30-50% (each trigger rolls independently)
_COMMENT_CHANCE_LO = 0.30
_COMMENT_CHANCE_HI = 0.50

# Triggers that always produce a comment (100% chance)
_GUARANTEED_TRIGGERS = {"game_won", "game_lost"}


def evaluate_ai_comment(
    state: GameState,
    ai_index: int,
    triggers: list[str],
    rng: Random,
) -> str | None:
    """Evaluate comment triggers and return a comment if one fires.

    ``triggers`` is a list of trigger names that apply to the current move.
    Each trigger has a 30-50% chance (rolled from rng) of producing a comment,
    except ``game_won`` and ``game_lost`` which always fire (100%).
    If multiple triggers fire, the first one that passes the chance check wins.

    Returns None if no comment is produced or if this is not an AI game.
    """
    ai_player = state.players[ai_index]
    if ai_player.player_type != "ai":
        return None
    difficulty = ai_player.ai_difficulty
    if difficulty is None:
        return None

    pools = _COMMENT_POOLS.get(difficulty)
    if pools is None:
        return None

    for trigger in triggers:
        pool = pools.get(trigger)
        if not pool:
            continue
        if trigger in _GUARANTEED_TRIGGERS:
            return rng.choice(pool)
        # Each trigger has its own chance threshold (30-50%)
        threshold = rng.uniform(_COMMENT_CHANCE_LO, _COMMENT_CHANCE_HI)
        if rng.random() < threshold:
            return rng.choice(pool)

    return None


def detect_ai_move_triggers(
    state_before: GameState,
    state_after: GameState,
    ai_index: int,
) -> list[str]:
    """Detect comment triggers after an AI move.

    Compares board state before/after to detect captures, plus, elemental, etc.
    """
    triggers: list[str] = []

    last_move = state_after.last_move
    if last_move is None:
        return triggers

    # ai_captured_cards: AI captured 1+ opponent cards
    cells_before = sum(
        1 for c in state_before.board if c is not None and c.owner == ai_index
    )
    cells_after = sum(
        1 for c in state_after.board if c is not None and c.owner == ai_index
    )
    # AI placed 1 card (+1 cell), any additional cells are captures
    new_captures = cells_after - cells_before - 1
    if new_captures > 0:
        triggers.append("ai_captured_cards")

    # plus_triggered
    if last_move.plus_triggered:
        triggers.append("plus_triggered")

    # elemental_triggered
    if last_move.elemental_triggered:
        triggers.append("elemental_triggered")

    # archetype_used: AI used its archetype this turn
    ai_before = state_before.players[ai_index]
    ai_after = state_after.players[ai_index]
    if not ai_before.archetype_used and ai_after.archetype_used:
        triggers.append("archetype_used")

    # game ending: use game_won/game_lost for clear outcomes, game_ending for draws
    empty_after = sum(1 for c in state_after.board if c is None)
    if empty_after == 0 or state_after.status != state_before.status:
        result = state_after.result
        if result is not None and not result.is_draw:
            if result.winner == ai_index:
                triggers.append("game_won")
            else:
                triggers.append("game_lost")
        else:
            triggers.append("game_ending")

    return triggers


def detect_human_move_triggers(
    state_before: GameState,
    state_after: GameState,
    ai_index: int,
) -> list[str]:
    """Detect 'reaction' triggers after a human move in an AI game.

    The AI reacts to the human capturing its cards or the human using an archetype.
    """
    triggers: list[str] = []

    last_move = state_after.last_move
    if last_move is None:
        return triggers

    # ai_got_captured: human captured AI's card(s)
    ai_cells_before = sum(
        1 for c in state_before.board if c is not None and c.owner == ai_index
    )
    ai_cells_after = sum(
        1 for c in state_after.board if c is not None and c.owner == ai_index
    )
    if ai_cells_after < ai_cells_before:
        triggers.append("ai_got_captured")

    # plus_triggered (human's plus)
    if last_move.plus_triggered:
        triggers.append("plus_triggered")

    # elemental_triggered (human's elemental)
    if last_move.elemental_triggered:
        triggers.append("elemental_triggered")

    # game ending: use game_won/game_lost for clear outcomes, game_ending for draws
    empty_after = sum(1 for c in state_after.board if c is None)
    if empty_after == 0 or state_after.status != state_before.status:
        result = state_after.result
        if result is not None and not result.is_draw:
            if result.winner == ai_index:
                triggers.append("game_won")
            else:
                triggers.append("game_lost")
        else:
            triggers.append("game_ending")

    return triggers
