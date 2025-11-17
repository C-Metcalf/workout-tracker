"""PySide6 application entry point with tabbed UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget, QWidget, QVBoxLayout

from workout.services import MealService, WorkoutService
from workout.storage import (
    JsonChatRepository,
    JsonDataStore,
    JsonMacroRepository,
    JsonMealRepository,
    JsonWorkoutRepository,
)
from workout.ui import ChatDockWidget, NutritionTab, WorkoutTab


def _default_data_path() -> Path:
    base = Path.cwd() / "data"
    base.mkdir(exist_ok=True)
    return base / "tracker.json"


class MainWindow(QMainWindow):
    """Main window wiring together services and widgets."""

    def __init__(self, data_path: Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Workout & Nutrition Tracker")
        self.resize(1280, 800)
        self._store = JsonDataStore(data_path or _default_data_path())

        # Services ---------------------------------------------------------
        workout_repo = JsonWorkoutRepository(self._store)
        meal_repo = JsonMealRepository(self._store)
        macro_repo = JsonMacroRepository(self._store)
        self.workout_service = WorkoutService(workout_repo)
        self.meal_service = MealService(meal_repo, macro_repo)
        self.chat_repo = JsonChatRepository(self._store)

        # UI ----------------------------------------------------------------
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        vbox = QVBoxLayout(central)

        self.tab_widget = QTabWidget()
        self.workout_tab = WorkoutTab(self.workout_service)
        self.nutrition_tab = NutritionTab(self.meal_service)
        self.tab_widget.addTab(self.workout_tab, "Workout")
        self.tab_widget.addTab(self.nutrition_tab, "Nutrition")
        vbox.addWidget(self.tab_widget)

        self.setCentralWidget(central)

        self.chat_dock = ChatDockWidget(self.chat_repo, self.workout_service, self.meal_service)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.chat_dock)

    def _connect_signals(self) -> None:
        for widget in (self.workout_tab, self.nutrition_tab, self.chat_dock):
            widget.statusMessage.connect(self.statusBar().showMessage)
            widget.errorOccurred.connect(self._show_error)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
