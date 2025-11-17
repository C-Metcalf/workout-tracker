"""Dockable chat panel placeholder for future AI integration."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from workout.domain.models import ChatMessage, ChatRole
from workout.domain.repositories import ChatRepository
from workout.services.meals import MealService
from workout.services.workouts import WorkoutService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatDockWidget(QDockWidget):
    """Simple chat log dock. AI responses arrive in Plan step 5."""

    statusMessage = Signal(str)
    errorOccurred = Signal(str)

    def __init__(
        self,
        repo: ChatRepository,
        workout_service: WorkoutService,
        meal_service: MealService,
        parent: QWidget | None = None,
    ):
        super().__init__("AI Coach", parent)
        self._repo = repo
        self._workout_service = workout_service
        self._meal_service = meal_service
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea
            | Qt.RightDockWidgetArea
            | Qt.BottomDockWidgetArea
        )
        self._build_ui()
        self._load_history()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Conversation"))
        self.message_list = QListWidget()
        layout.addWidget(self.message_list)

        self.input_field = QPlainTextEdit()
        self.input_field.setPlaceholderText("Ask for workout feedback or meal ideas...")
        layout.addWidget(self.input_field)

        controls = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._handle_send)
        self.clear_btn = QPushButton("Clear Chat")
        self.clear_btn.clicked.connect(self._clear_chat)
        controls.addWidget(self.send_btn)
        controls.addWidget(self.clear_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.setWidget(container)

    def _load_history(self) -> None:
        self.message_list.clear()
        for message in self._repo.history():
            self._append_message(message)

    def _handle_send(self) -> None:
        content = self.input_field.toPlainText().strip()
        if not content:
            return
        self.input_field.clear()
        try:
            user_message = ChatMessage(
                message_id=self._repo.next_message_id(),
                role=ChatRole.USER,
                content=content,
                created_at=_utcnow(),
            )
            self._repo.append(user_message)
            self._append_message(user_message)
            reply = self._build_placeholder_reply()
            self._repo.append(reply)
            self._append_message(reply)
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.statusMessage.emit("Message queued. AI responses coming soon.")

    def _build_placeholder_reply(self) -> ChatMessage:
        workout_summary = self._workout_service.summary()
        today_summary = self._meal_service.daily_summary(
            _utcnow().astimezone().date()
        )
        content = (
            "Assistant (preview): "
            f"{workout_summary.total_sessions} sessions logged with "
            f"{workout_summary.total_volume:.0f} lbs volume. Today's intake is "
            f"{today_summary.calories} kcal."
        )
        return ChatMessage(
            message_id=self._repo.next_message_id(),
            role=ChatRole.ASSISTANT,
            content=content,
            created_at=_utcnow(),
        )

    def _clear_chat(self) -> None:
        self._repo.clear()
        self._load_history()
        self.statusMessage.emit("Chat cleared.")

    def _append_message(self, message: ChatMessage) -> None:
        prefix = "You" if message.role == ChatRole.USER else "Coach"
        formatted = f"{prefix}: {message.content}"
        item = QListWidgetItem(formatted)
        self.message_list.addItem(item)
        self.message_list.scrollToBottom()
