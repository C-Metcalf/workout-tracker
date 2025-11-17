## UI Priorities

- **Tabs:** Keep current `Workout` and `Personal` tabs but add subtabs/panels for `Logger`, `History`, `Meals`, `Analytics`, and `AI Coach`.
- **Global Context:** persistent date range selector, profile summary banner (current weight, macros, streak) visible on every tab.
- **Shortcuts:** keyboard shortcuts for adding sessions/meals, toggling calendar, launching AI chat (`Ctrl+Enter`).

## Workout Logger

- Form for focus, perceived effort, duration, and dynamic table for sets (exercise, reps, weight, RIR).  
- Template buttons (“Push A”, “Lower B”) auto-fill exercises; drag handles to reorder sets.  
- Autosave draft + duplicate day option; inline validation (e.g., highlight invalid reps) with tooltip hints.

## Workout History & Analytics

- Table + filter panel for date range, focus, exercise; include inline sparkline for volume.  
- Pyqtgraph charts: stacked bar for volume per focus, line chart for PR progression, pie chart for sessions by focus.  
- Export button (CSV/PDF) and Quick Compare widget (pick 2 weeks/blocks).  
- Streak badge component showing current streak + best streak, clickable to reveal calendar heatmap.

## Nutrition Planner

- Meal entry form mirroring workout logger; auto-suggest foods from favorites list.  
- Daily summary card with macros vs goal, progress bars, and “sync with workout day” toggle.  
- Meal calendar showing color-coded adherence; click a day to open detail panel.

## AI Coach Panel

- Dockable chat window with transcript list, prompt dropdown (“Summarize week”, “Suggest meals”).  
- Input supports slash commands to insert last workout/meal summary.  
- Message bubbles show tokens/time, collapsible reasoning, and ability to pin advice to notes tab.

## UX & Design Guidelines

- **Consistency:** Shared component library (card, table, form field) w/ spacing scale (8px increments).  
- **Affordance:** Use icons + labels, clear hover states, disable actions until forms valid.  
- **Feedback:** Toasts/snackbars for saves, inline error banners for storage/network issues, skeleton loaders for charts.  
- **Accessibility:** High-contrast theme with optional dark mode, focus outlines, screen-reader labels via `accessibleName`.  
- **Responsiveness:** Adaptive grid—collapsible sidebar under 900px width, charts resize gracefully.  
- **Onboarding:** Provide guided tour overlay highlighting logger, history, AI panel on first run; add tooltips on controls.
