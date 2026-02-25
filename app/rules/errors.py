"""Domain errors raised by the rules engine reducer."""


class InvalidMoveError(Exception):
    """Base class for all illegal-move errors."""


class WrongPlayerTurnError(InvalidMoveError):
    """The acting player index does not match the current turn."""


class CardNotInHandError(InvalidMoveError):
    """The card being played is not in the player's hand."""


class OccupiedCellError(InvalidMoveError):
    """The target board cell is already occupied."""
