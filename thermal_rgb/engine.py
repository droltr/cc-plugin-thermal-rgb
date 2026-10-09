"""Temperature smoothing and the temperature-bands theme."""

import math
from collections.abc import Sequence

from .colors import RGB, ColorStop, gradient


class Ema:
    """Time-aware exponential moving average (time constant tau in seconds)."""

    def __init__(self, tau_s: float) -> None:
        self._tau_s = max(0.0, tau_s)
        self.value: float | None = None

    def update(self, sample: float, dt_s: float) -> float:
        if self.value is None or self._tau_s == 0:
            self.value = sample
        else:
            alpha = 1 - math.exp(-max(0.0, dt_s) / self._tau_s)
            self.value += alpha * (sample - self.value)
        return self.value


def bands_color(temp_c: float, stops: Sequence[ColorStop]) -> RGB:
    """Theme T1: every zone shows the gradient colour for the (smoothed) temperature."""
    return gradient(temp_c, stops)


def color_changed(old: RGB | None, new: RGB, threshold: int = 2) -> bool:
    """True when any channel moved by more than threshold (avoids redundant LED writes)."""
    return old is None or any(abs(a - b) > threshold for a, b in zip(old, new, strict=True))
