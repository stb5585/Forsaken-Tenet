"""Animator behavior for the combat view package."""

import math
import random

import pygame

DEATH_ANIMATION_FRAMES = 18


class SpriteAnimator:
    """Handles sprite animations (idle, bob, damage, death)."""

    def __init__(self):
        self.frame = 0
        self.animation_time = 0
        self.animation_type = None  # 'idle', 'damage', 'death', None
        self.bob_offset = 0
        self.sway_offset = 0
        self.damage_flash = 0  # 0-1, fades over time
        self.is_dead = False
        self.death_progress = 0  # 0-1, for scale/dissolve animation
        self.pace_span = random.uniform(16.0, 34.0)
        self.pace_period = random.uniform(105.0, 165.0)
        self.pace_phase = random.uniform(0.0, self.pace_period)

    def update(self, dt=1):
        """Update animation state. dt is frame time."""
        self.animation_time += dt

        # Idle idle animation (2-frame breathe/sway)
        if self.animation_type != "death":
            # Cycle between 0 and 1 every 60 frames (about 1 second at 60fps)
            self.frame = int((self.animation_time // 30) % 2)

        # Vertical bob (sine wave, continuous)
        bob_cycle = self.animation_time / 20  # Complete cycle every 20 frames
        self.bob_offset = math.sin(bob_cycle * math.pi * 2) * 8  # ±8 pixel bob

        # Horizontal sway (subtle idle motion for grounded enemies)
        sway_cycle = self.animation_time / 40  # Slower than bob
        self.sway_offset = math.sin(sway_cycle * math.pi * 2) * 3  # ±3 pixel sway

        # Damage flash decay
        if self.damage_flash > 0:
            self.damage_flash = max(0, self.damage_flash - 0.1)  # Fade over ~10 frames

        # Death animation progress
        if self.animation_type == "death":
            self.death_progress = min(1.0, self.animation_time / DEATH_ANIMATION_FRAMES)
            if self.death_progress >= 1.0:
                self.is_dead = True

    def confused_pace_offset(self) -> float:
        """Return a randomized back-and-forth offset with uncertain pauses."""
        cycle = ((self.animation_time + self.pace_phase) / self.pace_period) % 1.0
        if cycle < 0.14:
            position = -1.0
        elif cycle < 0.43:
            position = -1.0 + (cycle - 0.14) / 0.29 * 2.0
        elif cycle < 0.61:
            position = 1.0
        elif cycle < 0.90:
            position = 1.0 - (cycle - 0.61) / 0.29 * 2.0
        else:
            position = -1.0
        return position * self.pace_span

    def trigger_damage(self):
        """Trigger damage flash animation."""
        if self.animation_type == "death":
            return
        self.damage_flash = 1.0
        self.animation_type = None

    def trigger_death(self):
        """Trigger death animation."""
        if self.animation_type == "death" or self.is_dead:
            return
        self.animation_type = "death"
        self.animation_time = 0
        self.death_progress = 0
        self.damage_flash = 0  # Clear damage flash for clean death animation

    def apply_tint(self, surface, tint_color, strength):
        """Apply a tint overlay to a surface while preserving alpha channel."""
        if strength <= 0:
            return surface

        tinted = surface.copy()
        # Create RGB-only overlay (no alpha in fill)
        overlay = pygame.Surface(surface.get_size())
        overlay.fill(tint_color)
        overlay.set_alpha(int(strength * 128))
        # Use BLEND_RGB_ADD to affect only RGB channels, preserving original alpha
        tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tinted
