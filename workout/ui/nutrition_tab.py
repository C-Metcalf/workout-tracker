"""Nutrition tab for logging meals and tracking macros."""

from __future__ import annotations

from datetime import date, datetime, timezone

from PySide6.QtCore import QDate, QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from workout.services.meals import MealDaySummary, MealService


def _qdate_to_date(value: QDate) -> date:
    return value.toPython()


def _qdatetime_to_datetime(value: QDateTime) -> datetime:
    dt = value.toPython()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class NutritionTab(QWidget):
    """Form and analytics for meal tracking."""

    statusMessage = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, service: MealService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._build_ui()
        self._refresh_meals()
        self._update_daily_summary()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_logger())
        splitter.addWidget(self._build_history())
        splitter.setSizes([400, 800])
        layout.addWidget(splitter)

    def _build_logger(self) -> QWidget:
        box = QGroupBox("Log Meal")
        form_layout = QFormLayout(box)

        self.meal_datetime = QDateTimeEdit(QDateTime.currentDateTime())
        self.meal_datetime.setCalendarPopup(True)
        self.meal_name = QLineEdit()
        self.meal_name.setPlaceholderText("e.g. Breakfast, Protein Shake")
        self.calories_spin = QSpinBox()
        self.calories_spin.setRange(0, 6000)
        self.calories_spin.setSuffix(" kcal")
        self.protein_spin = QDoubleSpinBox()
        self.protein_spin.setRange(0.0, 300.0)
        self.protein_spin.setSuffix(" g")
        self.carbs_spin = QDoubleSpinBox()
        self.carbs_spin.setRange(0.0, 400.0)
        self.carbs_spin.setSuffix(" g")
        self.fats_spin = QDoubleSpinBox()
        self.fats_spin.setRange(0.0, 200.0)
        self.fats_spin.setSuffix(" g")

        form_layout.addRow("Date & Time", self.meal_datetime)
        form_layout.addRow("Name", self.meal_name)
        form_layout.addRow("Calories", self.calories_spin)
        form_layout.addRow("Protein", self.protein_spin)
        form_layout.addRow("Carbs", self.carbs_spin)
        form_layout.addRow("Fats", self.fats_spin)

        self.log_meal_btn = QPushButton("Save Meal")
        self.log_meal_btn.clicked.connect(self._save_meal)
        form_layout.addRow(self.log_meal_btn)
        return box

    def _build_history(self) -> QWidget:
        box = QGroupBox("Meals & Daily Summary")
        layout = QVBoxLayout(box)
        self.meal_day = QDateEdit(QDate.currentDate())
        self.meal_day.setCalendarPopup(True)
        self.meal_day.dateChanged.connect(self._update_daily_summary)

        day_row = QHBoxLayout()
        day_row.addWidget(QLabel("Summary Date"))
        day_row.addWidget(self.meal_day)
        day_row.addStretch()
        layout.addLayout(day_row)

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(0, 6000)
        self.goal_spin.setSuffix(" kcal goal")
        self.set_goal_btn = QPushButton("Set Goal")
        self.set_goal_btn.clicked.connect(self._set_goal)
        self.sync_summary_btn = QPushButton("Sync Summary")
        self.sync_summary_btn.clicked.connect(self._sync_summary)
        goal_row = QHBoxLayout()
        goal_row.addWidget(self.goal_spin)
        goal_row.addWidget(self.set_goal_btn)
        goal_row.addWidget(self.sync_summary_btn)
        layout.addLayout(goal_row)

        self.daily_summary_label = QLabel("")
        layout.addWidget(self.daily_summary_label)

        self.meals_table = QTableWidget(0, 6)
        self.meals_table.setHorizontalHeaderLabels(
            ["Time", "Name", "Calories", "Protein", "Carbs", "Fats"]
        )
        self.meals_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.meals_table)

        self.refresh_btn = QPushButton("Refresh Meals")
        self.refresh_btn.clicked.connect(self._refresh_meals)
        layout.addWidget(self.refresh_btn)
        return box

    def _save_meal(self) -> None:
        try:
            self._service.log_meal(
                consumed_at=_qdatetime_to_datetime(self.meal_datetime.dateTime()),
                name=self.meal_name.text(),
                calories=self.calories_spin.value(),
                protein_g=self.protein_spin.value(),
                carbs_g=self.carbs_spin.value(),
                fats_g=self.fats_spin.value(),
            )
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.statusMessage.emit("Meal saved.")
        self._refresh_meals()
        self._update_daily_summary()

    def _refresh_meals(self) -> None:
        try:
            meals = self._service.list_meals()
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.meals_table.setRowCount(0)
        for meal in meals:
            row = self.meals_table.rowCount()
            self.meals_table.insertRow(row)
            data = [
                meal.consumed_at.isoformat(timespec="minutes"),
                meal.name,
                str(meal.calories),
                f"{meal.protein_g:.1f}",
                f"{meal.carbs_g:.1f}",
                f"{meal.fats_g:.1f}",
            ]
            for column, value in enumerate(data):
                self.meals_table.setItem(row, column, QTableWidgetItem(value))

    def _set_goal(self) -> None:
        try:
            summary = self._service.set_calorie_goal(
                target_date=_qdate_to_date(self.meal_day.date()),
                calories_goal=self.goal_spin.value(),
            )
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.statusMessage.emit(
            f"Goal set to {summary.calories_goal} kcal for {summary.target_date.isoformat()}."
        )
        self._update_daily_summary()

    def _sync_summary(self) -> None:
        try:
            summary = self._service.sync_summary(
                target_date=_qdate_to_date(self.meal_day.date())
            )
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.statusMessage.emit(
            f"Summary synced for {summary.target_date.isoformat()}."
        )
        self._update_daily_summary()

    def _update_daily_summary(self) -> None:
        try:
            summary = self._service.daily_summary(
                target_date=_qdate_to_date(self.meal_day.date())
            )
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
            return
        self.daily_summary_label.setText(self._format_summary(summary))

    @staticmethod
    def _format_summary(summary: MealDaySummary) -> str:
        goal = summary.goal_calories or 0
        return (
            f"{summary.target_date:%Y-%m-%d}: {summary.calories} kcal "
            f"({summary.meals_count} meals)\n"
            f"Protein {summary.protein_g:.0f}g | Carbs {summary.carbs_g:.0f}g | "
            f"Fats {summary.fats_g:.0f}g | Goal {goal} kcal"
        )
