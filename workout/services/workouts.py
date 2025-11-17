"""Workout service layer with analytics helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from workout.domain.models import ExerciseSet, WorkoutSession
from workout.domain.repositories import WorkoutRepository


def _ensure_sets(sets: Iterable[ExerciseSet]) -> Sequence[ExerciseSet]:
    sets = tuple(sets)
    if not sets:
        raise ValueError("at least one exercise set is required")
    for item in sets:
        if item.reps <= 0:
            raise ValueError(f"invalid reps for {item.exercise}: {item.reps}")
        if item.weight < 0:
            raise ValueError(f"weight must be >= 0 for {item.exercise}")
    return sets


def _normalize_focus(value: str) -> str:
    focus = value.strip()
    if not focus:
        raise ValueError("session focus cannot be empty")
    return focus


@dataclass(frozen=True)
class WorkoutSummary:
    """Aggregated stats for a range of workout sessions."""

    start: Optional[date]
    end: Optional[date]
    total_sessions: int
    total_sets: int
    total_volume: float
    active_streak_days: int
    volume_by_exercise: Mapping[str, float]
    sessions_by_focus: Mapping[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "total_sessions": self.total_sessions,
            "total_sets": self.total_sets,
            "total_volume": self.total_volume,
            "active_streak_days": self.active_streak_days,
            "volume_by_exercise": dict(self.volume_by_exercise),
            "sessions_by_focus": dict(self.sessions_by_focus),
        }


class WorkoutService:
    """Coordinates workout persistence and analytics."""

    def __init__(self, repo: WorkoutRepository):
        self._repo = repo

    # CRUD -----------------------------------------------------------------

    def log_session(
        self,
        *,
        performed_on: date,
        focus: str,
        sets: Iterable[ExerciseSet],
        duration_minutes: Optional[int] = None,
        notes: str = "",
        session_id: Optional[str] = None,
    ) -> WorkoutSession:
        """Create or overwrite a session."""

        normalized_sets = _ensure_sets(sets)
        normalized_focus = _normalize_focus(focus)
        session = WorkoutSession(
            session_id=session_id or self._repo.next_session_id(),
            performed_on=performed_on,
            focus=normalized_focus,
            sets=normalized_sets,
            duration_minutes=duration_minutes,
            notes=notes.strip(),
        )
        self._repo.save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[WorkoutSession]:
        return self._repo.get_session(session_id)

    def delete_session(self, session_id: str) -> None:
        self._repo.delete_session(session_id)

    def list_sessions(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> Sequence[WorkoutSession]:
        sessions = self._repo.list_sessions(start=start, end=end)
        return sorted(sessions, key=lambda s: (s.performed_on, s.session_id))

    # Analytics -------------------------------------------------------------

    def summary(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> WorkoutSummary:
        sessions = self.list_sessions(start=start, end=end)
        volume_by_exercise: Dict[str, float] = {}
        sessions_by_focus: Dict[str, int] = {}
        total_sets = 0
        total_volume = 0.0

        for session in sessions:
            sessions_by_focus[session.focus] = sessions_by_focus.get(session.focus, 0) + 1
            for item in session.sets:
                total_sets += 1
                volume = item.weight * item.reps
                total_volume += volume
                volume_by_exercise[item.exercise] = (
                    volume_by_exercise.get(item.exercise, 0.0) + volume
                )

        streak = self.active_streak()
        return WorkoutSummary(
            start=start,
            end=end,
            total_sessions=len(sessions),
            total_sets=total_sets,
            total_volume=total_volume,
            active_streak_days=streak,
            volume_by_exercise=volume_by_exercise,
            sessions_by_focus=sessions_by_focus,
        )

    def active_streak(self, today: Optional[date] = None) -> int:
        """Return consecutive days with ≥1 session ending at latest workout."""

        sessions = self.list_sessions()
        if not sessions:
            return 0
        by_date: Dict[date, List[WorkoutSession]] = {}
        for session in sessions:
            by_date.setdefault(session.performed_on, []).append(session)

        sorted_dates = sorted(by_date.keys())
        if today is None:
            today = sorted_dates[-1]

        streak = 0
        cursor = today
        while cursor in by_date:
            streak += 1
            cursor = cursor - timedelta(days=1)
        return streak
