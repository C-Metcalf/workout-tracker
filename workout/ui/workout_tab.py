"""Workout tab widget with logging form, history table, and analytics."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Sequence

import pyqtgraph as pg
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
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

        self.sets_table = QTableWidget(0, 3)
        self.sets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sets_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sets_table.setHorizontalHeaderLabels(["Exercise", "Reps", "Weight (lbs)"])
        self.sets_table.horizontalHeader().setStretchLastSection(True)
        vbox.addWidget(self.sets_table)

        button_row = QHBoxLayout()
        self.add_set_btn = QPushButton("Add Set")
        self.add_set_btn.clicked.connect(self._add_set_row)
        self.remove_set_btn = QPushButton("Remove Selected")
        self.remove_set_btn.clicked.connect(self._remove_selected_set)

        button_row.addWidget(self.add_set_btn)
        button_row.addWidget(self.remove_set_btn)
        button_row.addStretch()
        vbox.addLayout(button_row)

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

    def _add_set_row(self) -> None:
        row = self.sets_table.rowCount()
        self.sets_table.insertRow(row)
        for column in range(3):
            self.sets_table.setItem(row, column, QTableWidgetItem(""))

    def _remove_selected_set(self) -> None:
        row = self.sets_table.currentRow()
        if row >= 0:
            self.sets_table.removeRow(row)

    def _populate_default_sets(self) -> None:
        for row in _default_sets_rows():
            self._add_set_row()
            row_index = self.sets_table.rowCount() - 1
            self.sets_table.item(row_index, 0).setText(row["exercise"])
            self.sets_table.item(row_index, 1).setText(row["reps"])
            self.sets_table.item(row_index, 2).setText(row["weight"])

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
        self.notes_edit.clear()
        self.focus_edit.clear()
        self._refresh_history()

    def _collect_sets(self) -> Sequence[ExerciseSet]:
        sets: List[ExerciseSet] = []
        for row in range(self.sets_table.rowCount()):
            exercise_item = self.sets_table.item(row, 0)
            reps_item = self.sets_table.item(row, 1)
            weight_item = self.sets_table.item(row, 2)
            if not exercise_item or not exercise_item.text().strip():
                continue
            try:
                reps = int(reps_item.text()) if reps_item else 0
                weight = float(weight_item.text()) if weight_item else 0.0
            except ValueError:
                raise ValueError("Ensure reps and weight are numeric.")
            sets.append(
                ExerciseSet(
                    exercise=exercise_item.text().strip(),
                    reps=reps,
                    weight=weight,
                )
            )
        return sets

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
