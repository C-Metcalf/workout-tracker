"""Workout tab widget with logging form, history table, and analytics."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence

import pyqtgraph as pg
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from workout.domain.models import ExerciseSet
from workout.services.workouts import WorkoutService, WorkoutSummary


def _qdate_to_pydate(value: QDate) -> date:
    return value.toPython()


def _default_sets_rows() -> List[Dict[str, str]]:
    return [
        {"exercise": "Bench Press", "reps": "8", "weight": "135"},
        {"exercise": "Incline DB Press", "reps": "10", "weight": "45"},
    ]


class WorkoutTab(QWidget):
    """Encapsulates the workout logging UI."""

    statusMessage = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, service: WorkoutService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._build_ui()
        self._populate_default_sets()
        self._refresh_history()

    # UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_filters())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_logger_panel())
        splitter.addWidget(self._build_history_panel())
        splitter.setSizes([400, 800])
        layout.addWidget(splitter)

    def _build_filters(self) -> QWidget:
        box = QGroupBox("History Filters")
        row = QHBoxLayout(box)
        self.start_filter = QDateEdit(QDate.currentDate().addDays(-7))
        self.start_filter.setCalendarPopup(True)
        self.end_filter = QDateEdit(QDate.currentDate())
        self.end_filter.setCalendarPopup(True)
        self.apply_filter_btn = QPushButton("Refresh")
        self.apply_filter_btn.clicked.connect(self._refresh_history)

        for widget, label in (
            (self.start_filter, "Start"),
            (self.end_filter, "End"),
        ):
            row.addWidget(QLabel(label))
            row.addWidget(widget)

        row.addStretch()
        row.addWidget(self.apply_filter_btn)
        return box

    def _build_logger_panel(self) -> QWidget:
        box = QGroupBox("Log Workout")
        vbox = QVBoxLayout(box)
        form = QFormLayout()
        self.session_date = QDateEdit(QDate.currentDate())
        self.session_date.setCalendarPopup(True)
        self.focus_edit = QLineEdit()
        self.focus_edit.setPlaceholderText("e.g. Push A, Pull B, Lower")
        self.duration_spin = QSpinBox()
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setRange(0, 300)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Add notes, RPE, or energy levels...")

        form.addRow("Date", self.session_date)
        form.addRow("Focus", self.focus_edit)
        form.addRow("Duration", self.duration_spin)
        form.addRow("Notes", self.notes_edit)
        vbox.addLayout(form)

        exercise_row = QHBoxLayout()
        self.exercise_name_input = QLineEdit()
        self.exercise_name_input.setPlaceholderText("Exercise name")
        self.add_exercise_btn = QPushButton("Add Exercise")
        self.add_exercise_btn.clicked.connect(self._add_exercise)
        exercise_row.addWidget(self.exercise_name_input)
        exercise_row.addWidget(self.add_exercise_btn)
        vbox.addLayout(exercise_row)

        self.exercises_view = QTreeWidget()
        self.exercises_view.setHeaderLabels(["Exercise", "Weight (lbs)", "Reps"])
        self.exercises_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.exercises_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.exercises_view.setRootIsDecorated(True)
        vbox.addWidget(self.exercises_view)

        set_row = QHBoxLayout()
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0.0, 2000.0)
        self.weight_input.setSuffix(" lbs")
        self.weight_input.setDecimals(1)
        self.reps_input = QSpinBox()
        self.reps_input.setRange(1, 100)
        self.add_set_btn = QPushButton("Add Set to Exercise")
        self.add_set_btn.clicked.connect(self._add_set_to_exercise)
        set_row.addWidget(QLabel("Weight"))
        set_row.addWidget(self.weight_input)
        set_row.addWidget(QLabel("Reps"))
        set_row.addWidget(self.reps_input)
        set_row.addWidget(self.add_set_btn)
        vbox.addLayout(set_row)

        self.save_workout_btn = QPushButton("Save Workout")
        self.save_workout_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        self.save_workout_btn.clicked.connect(self._save_workout)
        vbox.addWidget(self.save_workout_btn)

        return box

    def _build_history_panel(self) -> QWidget:
        box = QGroupBox("History & Analytics")
        vbox = QVBoxLayout(box)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setHorizontalHeaderLabels(
            ["Date", "Focus", "Sets", "Total Volume", "Notes"]
        )
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vbox.addWidget(self.history_table)

        summary_layout = QHBoxLayout()
        self.summary_total_sessions = QLabel("Sessions: 0")
        self.summary_total_sets = QLabel("Sets: 0")
        self.summary_volume = QLabel("Volume: 0 lbs")
        self.summary_streak = QLabel("Streak: 0 days")
        for label in (
            self.summary_total_sessions,
            self.summary_total_sets,
            self.summary_volume,
            self.summary_streak,
        ):
            label.setMinimumWidth(130)
            summary_layout.addWidget(label)
        summary_layout.addStretch()
        vbox.addLayout(summary_layout)

        self.volume_plot = pg.PlotWidget()
        self.volume_plot.setBackground("w")
        self.volume_plot.showGrid(x=True, y=True, alpha=0.3)
        self.volume_plot.setLabel("left", "Volume (lbs)")
        self.volume_plot.setLabel("bottom", "Exercise")
        vbox.addWidget(self.volume_plot)

        self.delete_session_btn = QPushButton("Delete Selected Session")
        self.delete_session_btn.clicked.connect(self._delete_selected_session)
        vbox.addWidget(self.delete_session_btn)

        return box

    # Slots ----------------------------------------------------------------

    def _add_exercise(self) -> None:
        name = self.exercise_name_input.text().strip()
        if not name:
            self.errorOccurred.emit("Enter an exercise name before adding.")
            return
        if self._find_exercise_item(name):
            self.errorOccurred.emit("Exercise already exists in the list.")
            return
        self._create_exercise_item(name)
        self.exercise_name_input.clear()

    def _add_set_to_exercise(self) -> None:
        exercise_item = self._current_exercise_item()
        if exercise_item is None:
            self.errorOccurred.emit("Select an exercise to append sets.")
            return
        weight = self.weight_input.value()
        reps = self.reps_input.value()
        if reps <= 0:
            self.errorOccurred.emit("Reps must be greater than zero.")
            return
        child = QTreeWidgetItem(["", f"{weight:.1f}", str(reps)])
        exercise_item.addChild(child)
        exercise_item.setExpanded(True)

    def _populate_default_sets(self) -> None:
        self.exercises_view.clear()
        for row in _default_sets_rows():
            exercise_item = self._create_exercise_item(row["exercise"])
            child = QTreeWidgetItem(["", row["weight"], row["reps"]])
            exercise_item.addChild(child)
            exercise_item.setExpanded(True)

    def _create_exercise_item(self, name: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name, "", ""])
        item.setExpanded(True)
        self.exercises_view.addTopLevelItem(item)
        return item

    def _find_exercise_item(self, name: str) -> Optional[QTreeWidgetItem]:
        lowered = name.lower()
        for index in range(self.exercises_view.topLevelItemCount()):
            item = self.exercises_view.topLevelItem(index)
            if item.text(0).lower() == lowered:
                return item
        return None

    def _current_exercise_item(self) -> Optional[QTreeWidgetItem]:
        item = self.exercises_view.currentItem()
        if item is None:
            return None
        return item if item.parent() is None else item.parent()

    def _save_workout(self) -> None:
        try:
            session_date = _qdate_to_pydate(self.session_date.date())
            focus = self.focus_edit.text()
            duration = self.duration_spin.value() or None
            notes = self.notes_edit.toPlainText()
            sets = self._collect_sets()
            if not sets:
                raise ValueError("Add at least one set before saving.")
            self._service.log_session(
                performed_on=session_date,
                focus=focus,
                sets=sets,
                duration_minutes=duration,
                notes=notes,
            )
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return

        self.statusMessage.emit("Workout saved.")
        self._clear_workout_form()
        self._refresh_history()

    def _collect_sets(self) -> Sequence[ExerciseSet]:
        sets: List[ExerciseSet] = []
        for index in range(self.exercises_view.topLevelItemCount()):
            exercise_item = self.exercises_view.topLevelItem(index)
            exercise_name = exercise_item.text(0).strip()
            if not exercise_name:
                continue
            for child_index in range(exercise_item.childCount()):
                child = exercise_item.child(child_index)
                weight_text = (child.text(1) or "").strip()
                reps_text = (child.text(2) or "").strip()
                try:
                    weight = float(weight_text or 0.0)
                    reps = int(reps_text or 0)
                except ValueError as exc:  # noqa: PERF203
                    raise ValueError("Ensure reps and weight are numeric.") from exc
                if reps <= 0:
                    raise ValueError(f"Invalid reps for {exercise_name}.")
                sets.append(
                    ExerciseSet(
                        exercise=exercise_name,
                        reps=reps,
                        weight=weight,
                    )
                )
        return sets

    def _clear_workout_form(self) -> None:
        self.session_date.setDate(QDate.currentDate())
        self.focus_edit.clear()
        self.duration_spin.setValue(0)
        self.notes_edit.clear()
        self.exercise_name_input.clear()
        self.exercises_view.clear()
        self.weight_input.setValue(0.0)
        self.reps_input.setValue(1)

    def _refresh_history(self) -> None:
        try:
            start = _qdate_to_pydate(self.start_filter.date())
            end = _qdate_to_pydate(self.end_filter.date())
            sessions = self._service.list_sessions(start=start, end=end)
            summary = self._service.summary(start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return

        self._populate_history_table(sessions)
        self._update_summary(summary)
        self._update_plot(summary)

    def _populate_history_table(self, sessions) -> None:
        self.history_table.setRowCount(0)
        for session in sessions:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            volume = sum(item.weight * item.reps for item in session.sets)
            sets_description = ", ".join(
                f"{item.exercise} ({item.reps}x{item.weight})" for item in session.sets
            )
            data = [
                session.performed_on.isoformat(),
                session.focus,
                sets_description,
                f"{volume:.0f}",
                session.notes,
            ]
            for column, value in enumerate(data):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, session.session_id)
                self.history_table.setItem(row, column, item)

    def _update_summary(self, summary: WorkoutSummary) -> None:
        self.summary_total_sessions.setText(f"Sessions: {summary.total_sessions}")
        self.summary_total_sets.setText(f"Sets: {summary.total_sets}")
        self.summary_volume.setText(f"Volume: {summary.total_volume:.0f} lbs")
        self.summary_streak.setText(f"Streak: {summary.active_streak_days} days")

    def _update_plot(self, summary: WorkoutSummary) -> None:
        self.volume_plot.clear()
        if not summary.volume_by_exercise:
            self.volume_plot.plot([0], [0])
            return
        exercises = list(summary.volume_by_exercise.keys())
        volumes = [summary.volume_by_exercise[name] for name in exercises]
        bg = pg.BarGraphItem(
            x=list(range(len(exercises))),
            height=volumes,
            width=0.6,
            brushes=[pg.intColor(i, len(exercises)) for i in range(len(exercises))],
        )
        self.volume_plot.addItem(bg)
        ax = self.volume_plot.getAxis("bottom")
        ax.setTicks([list(enumerate(exercises))])

    def _delete_selected_session(self) -> None:
        row = self.history_table.currentRow()
        if row < 0:
            return
        session_item = self.history_table.item(row, 0)
        session_id = session_item.data(Qt.ItemDataRole.UserRole)
        if not session_id:
            self.errorOccurred.emit("Could not determine selected session id.")
            return
        self._service.delete_session(session_id)
        self.statusMessage.emit("Session deleted.")
        self._refresh_history()
