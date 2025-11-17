"""JsonDataStore integration tests."""

from datetime import date, datetime, timedelta, timezone

from workout.domain.models import (
    ChatMessage,
    ChatRole,
    ExerciseSet,
    MacroSummary,
    MealEntry,
    WorkoutSession,
)
from workout.storage.json_store import (
    JsonChatRepository,
    JsonDataStore,
    JsonMacroRepository,
    JsonMealRepository,
    JsonWorkoutRepository,
)


def test_workout_repository_round_trip(tmp_path):
    store = JsonDataStore(tmp_path / "store.json")
    repo = JsonWorkoutRepository(store)

    session = WorkoutSession(
        session_id=repo.next_session_id(),
        performed_on=date(2025, 1, 2),
        focus="Legs",
        sets=(ExerciseSet(exercise="Squat", reps=5, weight=225.0),),
    )
    repo.save_session(session)

    assert repo.get_session(session.session_id) == session
    fetched = repo.list_sessions(start=date(2025, 1, 1), end=date(2025, 1, 3))
    assert fetched == [session]


def test_meal_repository_filters_by_datetime(tmp_path):
    store = JsonDataStore(tmp_path / "store.json")
    repo = JsonMealRepository(store)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    later = start + timedelta(hours=3)
    meal_one = MealEntry(
        meal_id=repo.next_meal_id(),
        consumed_at=start,
        name="Breakfast",
        calories=500,
        protein_g=30,
        carbs_g=70,
        fats_g=15,
    )
    meal_two = MealEntry(
        meal_id=repo.next_meal_id(),
        consumed_at=later,
        name="Snack",
        calories=200,
        protein_g=15,
        carbs_g=20,
        fats_g=5,
    )
    repo.save_meal(meal_one)
    repo.save_meal(meal_two)

    filtered = repo.list_meals(
        start=start + timedelta(minutes=90), end=later + timedelta(minutes=1)
    )
    assert filtered == [meal_two]


def test_macro_and_chat_repositories(tmp_path):
    store = JsonDataStore(tmp_path / "store.json")
    macro_repo = JsonMacroRepository(store)
    chat_repo = JsonChatRepository(store)

    summary = MacroSummary(
        summary_id=macro_repo.next_summary_id(),
        target_date=date(2025, 1, 3),
        calories=2300,
        protein_g=185,
        carbs_g=210,
        fats_g=70,
    )
    macro_repo.save_summary(summary)
    assert macro_repo.get_summary(summary.target_date) == summary

    message = ChatMessage(
        message_id=chat_repo.next_message_id(),
        role=ChatRole.USER,
        content="How was today's workout?",
        created_at=datetime(2025, 1, 3, tzinfo=timezone.utc),
    )
    chat_repo.append(message)
    assert chat_repo.history() == [message]
    chat_repo.clear()
    assert chat_repo.history() == []
