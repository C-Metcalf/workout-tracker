"""Service layer tests."""

from datetime import date, datetime, timezone

from workout.domain.models import ExerciseSet
from workout.storage.json_store import (
    JsonDataStore,
    JsonMacroRepository,
    JsonMealRepository,
    JsonWorkoutRepository,
)
from workout.services.meals import MealService
from workout.services.workouts import WorkoutService


def test_workout_service_summary_and_streak(tmp_path):
    store = JsonDataStore(tmp_path / "store.json")
    workout_repo = JsonWorkoutRepository(store)
    service = WorkoutService(workout_repo)

    service.log_session(
        performed_on=date(2025, 1, 1),
        focus="Push",
        sets=[
            ExerciseSet(exercise="Bench", reps=5, weight=135.0),
            ExerciseSet(exercise="Bench", reps=5, weight=145.0),
        ],
        duration_minutes=55,
    )
    service.log_session(
        performed_on=date(2025, 1, 2),
        focus="Pull",
        sets=[ExerciseSet(exercise="Row", reps=8, weight=95.0)],
    )

    summary = service.summary()
    assert summary.total_sessions == 2
    assert summary.total_sets == 3
    assert summary.volume_by_exercise["Bench"] == (135 * 5) + (145 * 5)
    assert summary.sessions_by_focus["Pull"] == 1
    assert service.active_streak() == 2


def test_meal_service_daily_summary_and_targets(tmp_path):
    store = JsonDataStore(tmp_path / "store.json")
    meal_repo = JsonMealRepository(store)
    macro_repo = JsonMacroRepository(store)
    service = MealService(meal_repo, macro_repo)

    consumed = datetime(2025, 1, 3, 8, 0, tzinfo=timezone.utc)
    service.log_meal(
        consumed_at=consumed,
        name="Breakfast",
        calories=450,
        protein_g=35,
        carbs_g=50,
        fats_g=15,
    )
    service.log_meal(
        consumed_at=consumed.replace(hour=12),
        name="Lunch",
        calories=600,
        protein_g=45,
        carbs_g=60,
        fats_g=20,
    )

    day = date(2025, 1, 3)
    summary = service.daily_summary(day)
    assert summary.calories == 1050
    assert summary.meals_count == 2

    service.set_calorie_goal(target_date=day, calories_goal=2200)
    stored = macro_repo.get_summary(day)
    assert stored is not None
    assert stored.calories_goal == 2200

    service.sync_summary(day)
    stored = macro_repo.get_summary(day)
    assert stored.calories == 1050
