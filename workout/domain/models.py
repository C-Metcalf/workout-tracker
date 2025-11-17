"""Domain models for the Workout tracker.

Invariants:
    * All identifiers are stable strings (UUIDs or composed keys).
    * Dates are stored as ISO-8601 strings (`YYYY-MM-DD`), datetimes as
      timezone-aware ISO strings.
    * Collections use tuples to enforce immutability within dataclasses.

Examples:
    >>> session = WorkoutSession(
    ...     session_id="session-1",
    ...     performed_on=date(2025, 1, 1),
    ...     focus="Pull A",
    ...     sets=(ExerciseSet(exercise="Pull Up", reps=8, weight=0.0),),
    ... )
    >>> session.to_dict()["performed_on"]
    '2025-01-01'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Tuple


class ChatRole(str, Enum):
    """Role of a chat message for AI interactions."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _require_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime values must be timezone-aware")
    return dt


def _serialize_datetime(dt: datetime) -> str:
    return _require_timezone(dt).isoformat()


def _deserialize_datetime(raw: str) -> datetime:
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None:
        raise ValueError("stored datetime lacks timezone info")
    return value


@dataclass(frozen=True)
class ExerciseSet:
    """Single recorded set in a workout."""

    exercise: str
    reps: int
    weight: float = 0.0
    weight_unit: str = "lbs"
    rir: Optional[float] = None  # Reps in reserve
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "exercise": self.exercise,
            "reps": self.reps,
            "weight": self.weight,
            "weight_unit": self.weight_unit,
            "rir": self.rir,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ExerciseSet":
        return cls(
            exercise=str(payload["exercise"]),
            reps=int(payload["reps"]),
            weight=float(payload.get("weight", 0.0)),
            weight_unit=str(payload.get("weight_unit", "lbs")),
            rir=float(payload["rir"]) if payload.get("rir") is not None else None,
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class WorkoutSession:
    """A structured record of a workout session."""

    session_id: str
    performed_on: date
    focus: str
    sets: Tuple[ExerciseSet, ...] = field(default_factory=tuple)
    duration_minutes: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "session_id": self.session_id,
            "performed_on": self.performed_on.isoformat(),
            "focus": self.focus,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "sets": [s.to_dict() for s in self.sets],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "WorkoutSession":
        sets_raw = payload.get("sets") or []
        sets = tuple(ExerciseSet.from_dict(item) for item in sets_raw)
        return cls(
            session_id=str(payload["session_id"]),
            performed_on=date.fromisoformat(str(payload["performed_on"])),
            focus=str(payload.get("focus", "")),
            duration_minutes=(
                int(payload["duration_minutes"])
                if payload.get("duration_minutes") is not None
                else None
            ),
            notes=str(payload.get("notes", "")),
            sets=sets,
        )


@dataclass(frozen=True)
class MealEntry:
    """Meal or snack tracked for nutrition."""

    meal_id: str
    consumed_at: datetime
    name: str
    calories: int
    protein_g: float
    carbs_g: float
    fats_g: float
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "meal_id": self.meal_id,
            "consumed_at": _serialize_datetime(self.consumed_at),
            "name": self.name,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fats_g": self.fats_g,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "MealEntry":
        return cls(
            meal_id=str(payload["meal_id"]),
            consumed_at=_deserialize_datetime(str(payload["consumed_at"])),
            name=str(payload.get("name", "")),
            calories=int(payload.get("calories", 0)),
            protein_g=float(payload.get("protein_g", 0.0)),
            carbs_g=float(payload.get("carbs_g", 0.0)),
            fats_g=float(payload.get("fats_g", 0.0)),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class MacroSummary:
    """Daily aggregation of macro nutrients."""

    summary_id: str
    target_date: date
    calories: int
    protein_g: float
    carbs_g: float
    fats_g: float
    calories_goal: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary_id": self.summary_id,
            "target_date": self.target_date.isoformat(),
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fats_g": self.fats_g,
            "calories_goal": self.calories_goal,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "MacroSummary":
        return cls(
            summary_id=str(payload["summary_id"]),
            target_date=date.fromisoformat(str(payload["target_date"])),
            calories=int(payload.get("calories", 0)),
            protein_g=float(payload.get("protein_g", 0.0)),
            carbs_g=float(payload.get("carbs_g", 0.0)),
            fats_g=float(payload.get("fats_g", 0.0)),
            calories_goal=(
                int(payload["calories_goal"])
                if payload.get("calories_goal") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class ChatMessage:
    """Chat transcripts for AI assistant interactions."""

    message_id: str
    role: ChatRole
    content: str
    created_at: datetime
    metadata: MutableMapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "created_at": _serialize_datetime(self.created_at),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ChatMessage":
        role = ChatRole(str(payload.get("role", ChatRole.USER.value)))
        metadata = dict(payload.get("metadata") or {})
        return cls(
            message_id=str(payload["message_id"]),
            role=role,
            content=str(payload.get("content", "")),
            created_at=_deserialize_datetime(str(payload["created_at"])),
            metadata=metadata,
        )


DomainModel = ExerciseSet | WorkoutSession | MealEntry | MacroSummary | ChatMessage


def as_dict(model: DomainModel) -> Dict[str, object]:
    """Polymorphic helper for serialization."""

    return model.to_dict()


def from_dict(model_type, payload: Mapping[str, object]) -> DomainModel:
    """Dispatch helper to reconstruct a domain object."""

    return model_type.from_dict(payload)
