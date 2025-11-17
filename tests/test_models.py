"""Model serialization tests."""

from datetime import date, datetime, timezone

from workout.domain.models import (
    ChatMessage,
    ChatRole,
    ExerciseSet,
    MacroSummary,
    MealEntry,
    WorkoutSession,
)


def test_workout_session_serialization_round_trip():
    session = WorkoutSession(
        session_id="session-123",
        performed_on=date(2025, 1, 1),
        focus="Push A",
        sets=(
            ExerciseSet(exercise="Bench", reps=6, weight=135.0, weight_unit="lbs"),
            ExerciseSet(exercise="Incline DB", reps=10, weight=45.0),
        ),
        duration_minutes=55,
        notes="Felt strong",
    )

    restored = WorkoutSession.from_dict(session.to_dict())
    assert restored == session


def test_meal_and_macro_round_trip():
    now = datetime(2025, 1, 1, 7, 30, tzinfo=timezone.utc)
    meal = MealEntry(
        meal_id="meal-1",
        consumed_at=now,
        name="Oats",
        calories=350,
        protein_g=25.0,
        carbs_g=45.0,
        fats_g=8.0,
    )
    summary = MacroSummary(
        summary_id="macro-1",
        target_date=date(2025, 1, 1),
        calories=2200,
        protein_g=180.0,
        carbs_g=220.0,
        fats_g=60.0,
        calories_goal=2400,
    )

    assert MealEntry.from_dict(meal.to_dict()) == meal
    assert MacroSummary.from_dict(summary.to_dict()) == summary


def test_chat_message_round_trip():
    message = ChatMessage(
        message_id="chat-1",
        role=ChatRole.USER,
        content="Hello",
        created_at=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    assert ChatMessage.from_dict(message.to_dict()) == message
