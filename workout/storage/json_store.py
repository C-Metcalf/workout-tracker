"""JSON-backed repositories for workout data."""

from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Any, Callable, Dict, Iterable, List, MutableMapping, Optional, Sequence

from workout.domain.models import (
    ChatMessage,
    MacroSummary,
    MealEntry,
    WorkoutSession,
)
from workout.domain.repositories import (
    ChatRepository,
    MacroSummaryRepository,
    MealRepository,
    RepositoryError,
    WorkoutRepository,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_SCHEMA_VERSION = 1
DEFAULT_DATASET = {
    "version": DEFAULT_SCHEMA_VERSION,
    "workouts": [],
    "meals": [],
    "macros": [],
    "chat": [],
}


class SchemaVersionError(RepositoryError):
    """Raised when the on-disk schema is incompatible with the adapter."""


class JsonDataStore:
    """Thread-safe helper to read/write versioned JSON payloads."""

    def __init__(self, path: str | Path, schema_version: int = DEFAULT_SCHEMA_VERSION):
        self.path = Path(path)
        self.schema_version = schema_version
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_locked(copy.deepcopy(DEFAULT_DATASET))

    def load(self) -> Dict[str, Any]:
        """Return a deep copy of the dataset."""

        with self._lock:
            data = self._read_locked()
        return data

    def update(self, mutator: Callable[[MutableMapping[str, Any]], None]) -> None:
        """Apply a mutation inside the file lock and persist the result."""

        with self._lock:
            data = self._read_locked()
            mutator(data)
            self._write_locked(data)

    # Internal helpers -----------------------------------------------------

    def _ensure_sections(self, data: MutableMapping[str, Any]) -> None:
        for key in ("workouts", "meals", "macros", "chat"):
            data.setdefault(key, [])

    def _read_locked(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("version") != self.schema_version:
            raise SchemaVersionError(
                f"Unsupported schema {payload.get('version')} != {self.schema_version}"
            )
        self._ensure_sections(payload)
        return copy.deepcopy(payload)

    def _write_locked(self, data: MutableMapping[str, Any]) -> None:
        self._ensure_sections(data)
        data["version"] = self.schema_version
        tmp_path = None
        with NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=str(self.path.parent)
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        if self.path.exists():
            shutil.copy2(self.path, backup_path)
        tmp_path.replace(self.path)


def _filter_by_date_range(
    items: Sequence[WorkoutSession],
    start: Optional[date],
    end: Optional[date],
) -> List[WorkoutSession]:
    results: List[WorkoutSession] = []
    for item in items:
        if start and item.performed_on < start:
            continue
        if end and item.performed_on > end:
            continue
        results.append(item)
    return results


def _filter_meals_by_range(
    items: Sequence[MealEntry],
    start: Optional[datetime],
    end: Optional[datetime],
) -> List[MealEntry]:
    results: List[MealEntry] = []
    for item in items:
        if start and item.consumed_at < start:
            continue
        if end and item.consumed_at > end:
            continue
        results.append(item)
    return results


class JsonWorkoutRepository(WorkoutRepository):
    """Workout repository backed by JsonDataStore."""

    def __init__(self, store: JsonDataStore):
        self.store = store

    def list_sessions(self, start=None, end=None) -> Sequence[WorkoutSession]:
        data = self.store.load()
        sessions = [WorkoutSession.from_dict(item) for item in data["workouts"]]
        return _filter_by_date_range(sessions, start, end)

    def get_session(self, session_id: str) -> Optional[WorkoutSession]:
        data = self.store.load()["workouts"]
        for row in data:
            if row["session_id"] == session_id:
                return WorkoutSession.from_dict(row)
        return None

    def save_session(self, session: WorkoutSession) -> None:
        payload = session.to_dict()

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            rows = dataset["workouts"]
            for index, row in enumerate(rows):
                if row["session_id"] == session.session_id:
                    rows[index] = payload
                    break
            else:
                rows.append(payload)

        self.store.update(mutate)

    def delete_session(self, session_id: str) -> None:

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            rows = dataset["workouts"]
            dataset["workouts"] = [row for row in rows if row["session_id"] != session_id]

        self.store.update(mutate)

    def next_session_id(self) -> str:
        return f"session-{uuid.uuid4().hex}"


class JsonMealRepository(MealRepository):
    """Meal repository backed by JsonDataStore."""

    def __init__(self, store: JsonDataStore):
        self.store = store

    def list_meals(self, start=None, end=None) -> Sequence[MealEntry]:
        meals = [MealEntry.from_dict(row) for row in self.store.load()["meals"]]
        return _filter_meals_by_range(meals, start, end)

    def save_meal(self, meal: MealEntry) -> None:
        payload = meal.to_dict()

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            rows = dataset["meals"]
            for index, row in enumerate(rows):
                if row["meal_id"] == meal.meal_id:
                    rows[index] = payload
                    break
            else:
                rows.append(payload)

        self.store.update(mutate)

    def delete_meal(self, meal_id: str) -> None:

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            rows = dataset["meals"]
            dataset["meals"] = [row for row in rows if row["meal_id"] != meal_id]

        self.store.update(mutate)

    def next_meal_id(self) -> str:
        return f"meal-{uuid.uuid4().hex}"


class JsonMacroRepository(MacroSummaryRepository):
    """Macro summary repository backed by JsonDataStore."""

    def __init__(self, store: JsonDataStore):
        self.store = store

    def get_summary(self, target_date) -> Optional[MacroSummary]:
        for row in self.store.load()["macros"]:
            if row["target_date"] == target_date.isoformat():
                return MacroSummary.from_dict(row)
        return None

    def list_summaries(self, start=None, end=None) -> Sequence[MacroSummary]:
        summaries = [MacroSummary.from_dict(row) for row in self.store.load()["macros"]]
        if not start and not end:
            return summaries
        result: List[MacroSummary] = []
        for summary in summaries:
            if start and summary.target_date < start:
                continue
            if end and summary.target_date > end:
                continue
            result.append(summary)
        return result

    def save_summary(self, summary: MacroSummary) -> None:
        payload = summary.to_dict()

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            rows = dataset["macros"]
            for index, row in enumerate(rows):
                if row["summary_id"] == summary.summary_id:
                    rows[index] = payload
                    break
            else:
                rows.append(payload)

        self.store.update(mutate)

    def next_summary_id(self) -> str:
        return f"macro-{uuid.uuid4().hex}"


class JsonChatRepository(ChatRepository):
    """Chat transcript repository backed by JsonDataStore."""

    def __init__(self, store: JsonDataStore):
        self.store = store

    def history(self, limit: Optional[int] = None) -> Sequence[ChatMessage]:
        messages = [ChatMessage.from_dict(row) for row in self.store.load()["chat"]]
        if limit is not None:
            return list(messages[-limit:])
        return messages

    def append(self, message: ChatMessage) -> None:
        payload = message.to_dict()

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            dataset["chat"].append(payload)

        self.store.update(mutate)

    def replace(self, messages: Iterable[ChatMessage]) -> None:
        payload = [msg.to_dict() for msg in messages]

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            dataset["chat"] = payload

        self.store.update(mutate)

    def clear(self) -> None:

        def mutate(dataset: MutableMapping[str, Any]) -> None:
            dataset["chat"] = []

        self.store.update(mutate)

    def next_message_id(self) -> str:
        return f"chat-{uuid.uuid4().hex}"
