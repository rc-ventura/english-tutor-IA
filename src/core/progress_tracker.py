from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

"""Module for tracking user progress such as XP, badges, completed tasks, etc.

This module is intentionally lightweight so it can be reused by tutors and the UI
without additional dependencies.  All rendering is done via simple HTML snippets
that are embedded in the Gradio interface.

Future improvements (e.g., persistent storage) can be implemented in this class
without touching the rest of the codebase.
"""


@dataclass(slots=True)
class BadgeDefinition:
    """Configuration for a badge unlock.

    Attributes
    ----------
    name : str
        Display name of the badge.
    description : str
        Short description shown in the dashboard.
    threshold : int
        XP threshold required to unlock the badge.
    """

    name: str
    description: str
    threshold: int


@dataclass
class ProgressTracker:
    """Simple XP, badge and task tracker for the user."""

    def __init__(self):
        self.xp: int = 0
        self.tasks_completed: int = 0
        self.skills: dict[str, int] = {"grammar": 0, "vocabulary": 0, "pronunciation": 0}

        # Badge definitions - XP thresholds must be > 0 for XP-based badges
        self.BADGES: List[BadgeDefinition] = [
            BadgeDefinition(name="First Steps", description="Earn 50 XP", threshold=50),
            BadgeDefinition(name="Getting Warmer", description="Earn 200 XP", threshold=200),
            BadgeDefinition(name="Rising Star", description="Earn 500 XP", threshold=500),
            BadgeDefinition(name="Master", description="Earn 1000 XP", threshold=1000),
            # Task-based badge (threshold=0 means it's not XP-based)
            BadgeDefinition(name="Wordsmith", description="Complete 10 writing tasks", threshold=0),
        ]
        self.badges: List[str] = []

    def add_xp(self, amount: int) -> None:
        """Add XP and check for new badges."""
        if amount <= 0:
            return
        self.xp += amount
        self._check_badges()

    def increment_tasks(self, count: int = 1) -> None:
        """Increment completed tasks counter and check task-based badges."""
        if count <= 0:
            return
        self.tasks_completed += count
        self._check_badges()

    def update_skill(self, skill: str, points: int):
        """Update skill level and check for skill badges"""
        if skill in self.skills:
            self.skills[skill] += points
            if skill == "grammar" and self.skills[skill] >= 50:
                self._award_badge("Grammar Guru")

    # ---------------------------------------------------------------------
    # Rendering helpers
    # ---------------------------------------------------------------------
    def html_dashboard(self) -> str:
        """Generate HTML snippet showing user progress."""
        badges_html = ""
        if self.badges:
            badges_html = "".join(f"<li class='badge'>{badge}</li>" for badge in self.badges)
        else:
            badges_html = "<li>No badges yet</li>"

        skills_html = "".join(f"<li>{skill}: {level}</li>" for skill, level in self.skills.items())

        return f"""
        <div class='progress-dashboard'>
            <h2>User Progress</h2>
            <p>Total XP: {self.xp}</p>
            <div class='progress-bar-outer'>
                <div class='progress-bar-inner' style='width:{min(100, self.xp/10)}%'></div>
            </div>
            <h3>Skills</h3>
            <ul>{skills_html}</ul>
            <h3>Badges</h3>
            <ul class='badge-list'>{badges_html}</ul>
        </div>
        """

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _check_badges(self) -> None:
        """Check if user qualifies for any new badges."""
        for badge_def in self.BADGES:
            if badge_def.name not in self.badges:
                # XP-based badges (threshold > 0)
                if badge_def.threshold > 0 and self.xp >= badge_def.threshold:
                    self._award_badge(badge_def.name)
                # Special case for task-based badges (threshold=0)
                elif badge_def.name == "Wordsmith" and self.tasks_completed >= 10:
                    self._award_badge(badge_def.name)

    def _award_badge(self, badge_name: str) -> None:
        """Award a badge to the user."""
        if badge_name not in self.badges:
            self.badges.append(badge_name)
