"""Severity classification for detected threats.

This module defines the :class:`Severity` enum, which assigns a normalised
numeric weight to each threat level.  Weights are consumed by the risk-score
calculator in :mod:`app.core.utils`.
"""

from enum import Enum


class Severity(Enum):
    """Ordered threat-severity levels with corresponding risk weights.

    Each member carries a ``weight`` attribute in the ``[0.0, 1.0]`` range.
    Higher weights contribute more to the aggregate risk score returned by the
    detection engine.

    Attributes:
        LOW: Minor or informational findings (weight 0.10).
        MEDIUM: Noteworthy issues that warrant attention (weight 0.40).
        HIGH: Serious threats that likely require immediate review (weight 0.70).
        CRITICAL: Severe threats demanding instant mitigation (weight 1.00).

    Example::

        >>> Severity.HIGH.weight
        0.7
        >>> sorted(Severity, key=lambda s: s.weight)
        [<Severity.LOW: 0.1>, <Severity.MEDIUM: 0.4>, ...]
    """

    LOW = 0.10
    MEDIUM = 0.40
    HIGH = 0.70
    CRITICAL = 1.00

    @property
    def weight(self) -> float:
        """Return the numeric risk weight for this severity level.

        Returns:
            float: A value in the range ``[0.0, 1.0]``.
        """
        return float(self.value)

    def __lt__(self, other: "Severity") -> bool:  # noqa: D105
        if not isinstance(other, Severity):
            return NotImplemented
        return self.weight < other.weight

    def __le__(self, other: "Severity") -> bool:  # noqa: D105
        if not isinstance(other, Severity):
            return NotImplemented
        return self.weight <= other.weight

    def __gt__(self, other: "Severity") -> bool:  # noqa: D105
        if not isinstance(other, Severity):
            return NotImplemented
        return self.weight > other.weight

    def __ge__(self, other: "Severity") -> bool:  # noqa: D105
        if not isinstance(other, Severity):
            return NotImplemented
        return self.weight >= other.weight
