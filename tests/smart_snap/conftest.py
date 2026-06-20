"""Shared fixtures for Smart Snap POC-1 tests."""
from __future__ import annotations

import math
import numpy as np
import pytest


def make_ball_image(
    width: int = 320,
    height: int = 240,
    ball_cx: int = 160,
    ball_cy: int = 120,
    ball_radius: int = 20,
    bg_color: tuple = (80, 80, 80),
    ball_color: tuple = (255, 255, 255),
) -> np.ndarray:
    """Return a synthetic RGB image with a filled circle (ball)."""
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)
    yy, xx = np.ogrid[:height, :width]
    mask = (xx - ball_cx) ** 2 + (yy - ball_cy) ** 2 <= ball_radius ** 2
    img[mask] = ball_color
    return img


def make_empty_image(width: int = 320, height: int = 240) -> np.ndarray:
    """Return a plain grey image with no discernible features."""
    return np.full((height, width, 3), 128, dtype=np.uint8)


@pytest.fixture
def ball_image():
    """320×240 RGB with 20px-radius white ball centred at (160,120)."""
    return make_ball_image()


@pytest.fixture
def empty_image():
    """320×240 flat grey image — no ball."""
    return make_empty_image()


@pytest.fixture
def ball_image_edge():
    """320×240 RGB with ball near the left edge (cx=18, cy=120)."""
    return make_ball_image(ball_cx=18, ball_cy=120, ball_radius=15)
