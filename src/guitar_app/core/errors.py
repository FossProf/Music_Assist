"""Domain-specific exceptions shared across the core engines.

Exceptions are grouped here in one module so that low-level modules can raise
domain errors without importing from one another (avoiding import cycles).
"""


class InvalidPitchError(ValueError):
    """Raised when a pitch or pitch-class cannot be parsed or constructed."""


class InvalidTuningError(ValueError):
    """Raised when a tuning or guitar string is malformed."""


class InvalidPositionError(ValueError):
    """Raised when a string/fret position does not exist on a fretboard."""


class InvalidScaleDegreeError(ValueError):
    """Raised for invalid scale degrees or malformed scale formulas."""
