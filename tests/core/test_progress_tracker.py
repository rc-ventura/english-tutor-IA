import pytest

from src.core.progress_tracker import ProgressTracker


def test_add_xp_unlocks_badge():
    tracker = ProgressTracker()
    # Earn 60 XP – should unlock "First Steps" (threshold 50)
    tracker.add_xp(60)
    assert tracker.xp == 60
    assert "First Steps" in tracker.badges


def test_increment_tasks_unlocks_wordsmith():
    tracker = ProgressTracker()
    # Complete 10 tasks
    for _ in range(10):
        tracker.increment_tasks()
    assert tracker.tasks_completed == 10
    assert "Wordsmith" in tracker.badges


def test_html_dashboard_reflects_state():
    tracker = ProgressTracker()
    tracker.add_xp(120)
    html = tracker.html_dashboard()
    # Ensure XP appears in the HTML
    assert str(tracker.xp) in html
    # Earn badge and verify it's in HTML
    assert "First Steps" in html


def test_multiple_xp_increments():
    tracker = ProgressTracker()
    tracker.add_xp(30)
    tracker.add_xp(40)
    assert tracker.xp == 70
    assert "First Steps" in tracker.badges  # Threshold 50 XP


def test_skill_tracking():
    tracker = ProgressTracker()
    tracker.update_skill("grammar", 5)
    tracker.update_skill("vocabulary", 3)
    assert tracker.skills["grammar"] == 5
    assert tracker.skills["vocabulary"] == 3
    assert "grammar: 5" in tracker.html_dashboard()


def test_edge_cases():
    tracker = ProgressTracker()
    # Test XP negativo
    tracker.add_xp(-10)
    assert tracker.xp == 0

    # Teste muitas tarefas
    for _ in range(10):
        tracker.increment_tasks()
    assert tracker.tasks_completed == 10
    assert "Wordsmith" in tracker.badges


def test_badge_progression():
    tracker = ProgressTracker()
    # Teste progressão de badges
    assert len(tracker.badges) == 0
    tracker.add_xp(40)
    assert len(tracker.badges) == 0  # Ainda não atingiu threshold
    tracker.add_xp(20)  # Total 60 XP
    assert "First Steps" in tracker.badges
    tracker.add_xp(200)  # Total 260 XP
    assert "Getting Warmer" in tracker.badges
