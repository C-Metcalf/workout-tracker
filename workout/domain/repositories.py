"""Repository contracts for the Workout tracker.

The UI and service layers speak in terms of these ports so that storage and
network adapters can be swapped without changing business logic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional, Protocol, Sequence

from .models import ChatMessage, MacroSummary, MealEntry, WorkoutSession


class RepositoryError(RuntimeError):
    """Base exception raised when repository operations fail."""


class WorkoutRepository(Protocol):
    """Port for workout session persistence."""

    def list_sessions(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> Sequence[WorkoutSession]:
        ...

    def get_session(self, session_id: str) -> Optional[WorkoutSession]:
        ...

    def save_session(self, session: WorkoutSession) -> None:
        ...

    def delete_session(self, session_id: str) -> None:
        ...

    def next_session_id(self) -> str:
        ...


class MealRepository(Protocol):
    """Port for meal entries."""

    def list_meals(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> Sequence[MealEntry]:
        ...

    def save_meal(self, meal: MealEntry) -> None:
        ...

    def delete_meal(self, meal_id: str) -> None:
        ...

    def next_meal_id(self) -> str:
        ...


class MacroSummaryRepository(Protocol):
    """Port for macro summaries."""

    def get_summary(self, target_date: date) -> Optional[MacroSummary]:
        ...

    def list_summaries(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> Sequence[MacroSummary]:
        ...

    def save_summary(self, summary: MacroSummary) -> None:
        ...

    def next_summary_id(self) -> str:
        ...


class ChatRepository(Protocol):
    """Port for chat transcripts."""

    def history(self, limit: Optional[int] = None) -> Sequence[ChatMessage]:
        ...

    def append(self, message: ChatMessage) -> None:
        ...

    def replace(self, messages: Iterable[ChatMessage]) -> None:
        ...

    def clear(self) -> None:
        ...

    def next_message_id(self) -> str:
        ...
