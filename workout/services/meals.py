"""Meal and macro service layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional, Sequence

from workout.domain.models import MacroSummary, MealEntry
from workout.domain.repositories import MacroSummaryRepository, MealRepository


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("consumed_at must be timezone-aware")
    return value


def _non_negative(name: str, value: float) -> float:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


@dataclass(frozen=True)
class MealDaySummary:
    """Per-day macro totals derived from meal entries."""

    target_date: date
    calories: int
    protein_g: float
    carbs_g: float
    fats_g: float
    goal_calories: Optional[int]
    meals_count: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "target_date": self.target_date.isoformat(),
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fats_g": self.fats_g,
            "goal_calories": self.goal_calories,
            "meals_count": self.meals_count,
        }


class MealService:
    """Coordinates meal entries and macro summaries."""

    def __init__(
        self,
        meal_repo: MealRepository,
        summary_repo: MacroSummaryRepository,
    ):
        self._meal_repo = meal_repo
        self._summary_repo = summary_repo

    # CRUD -----------------------------------------------------------------

    def log_meal(
        self,
        *,
        consumed_at: datetime,
        name: str,
        calories: int,
        protein_g: float,
        carbs_g: float,
        fats_g: float,
        notes: str = "",
        meal_id: Optional[str] = None,
    ) -> MealEntry:
        """Store a meal entry with validation."""

        if not name.strip():
            raise ValueError("meal name cannot be empty")
        consumed_at = _ensure_timezone(consumed_at)
        calories = int(_non_negative("calories", calories))

        entry = MealEntry(
            meal_id=meal_id or self._meal_repo.next_meal_id(),
            consumed_at=consumed_at,
            name=name.strip(),
            calories=calories,
            protein_g=_non_negative("protein_g", protein_g),
            carbs_g=_non_negative("carbs_g", carbs_g),
            fats_g=_non_negative("fats_g", fats_g),
            notes=notes.strip(),
        )
        self._meal_repo.save_meal(entry)
        return entry

    def delete_meal(self, meal_id: str) -> None:
        self._meal_repo.delete_meal(meal_id)

    def list_meals(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> Sequence[MealEntry]:
        return sorted(
            self._meal_repo.list_meals(start=start, end=end),
            key=lambda meal: meal.consumed_at,
        )

    # Summaries ------------------------------------------------------------

    def set_calorie_goal(
        self,
        *,
        target_date: date,
        calories_goal: int,
    ) -> MacroSummary:
        totals = self._meal_totals(target_date)
        existing = self._summary_repo.get_summary(target_date)
        goal = int(_non_negative("calories_goal", calories_goal))
        summary = MacroSummary(
            summary_id=existing.summary_id if existing else self._summary_repo.next_summary_id(),
            target_date=target_date,
            calories=totals["calories"],
            protein_g=totals["protein_g"],
            carbs_g=totals["carbs_g"],
            fats_g=totals["fats_g"],
            calories_goal=goal,
        )
        self._summary_repo.save_summary(summary)
        return summary

    def sync_summary(self, target_date: date) -> MacroSummary:
        """Persist aggregated macros for a given date."""

        totals = self._meal_totals(target_date)
        existing = self._summary_repo.get_summary(target_date)
        summary = MacroSummary(
            summary_id=existing.summary_id if existing else self._summary_repo.next_summary_id(),
            target_date=target_date,
            calories=totals["calories"],
            protein_g=totals["protein_g"],
            carbs_g=totals["carbs_g"],
            fats_g=totals["fats_g"],
            calories_goal=existing.calories_goal if existing else None,
        )
        self._summary_repo.save_summary(summary)
        return summary

    def daily_summary(self, target_date: date) -> MealDaySummary:
        totals = self._meal_totals(target_date)
        goal = self._summary_repo.get_summary(target_date)

        return MealDaySummary(
            target_date=target_date,
            calories=totals["calories"],
            protein_g=totals["protein_g"],
            carbs_g=totals["carbs_g"],
            fats_g=totals["fats_g"],
            goal_calories=goal.calories_goal if goal else None,
            meals_count=totals["count"],
        )

    # Internal helpers -----------------------------------------------------

    def _meal_totals(self, target_date: date) -> Dict[str, float]:
        meals = [
            meal for meal in self.list_meals() if meal.consumed_at.date() == target_date
        ]
        return {
            "calories": sum(meal.calories for meal in meals),
            "protein_g": sum(meal.protein_g for meal in meals),
            "carbs_g": sum(meal.carbs_g for meal in meals),
            "fats_g": sum(meal.fats_g for meal in meals),
            "count": len(meals),
        }
