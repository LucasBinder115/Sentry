📘 Project Name

sentry.inc

(Temporary codename for a full OCR-driven logistics management system.)

🎯 General Objective

The sentry.inc project is designed to manage and automate the recognition of vehicle license plates through OCR technology, supporting logistics and transport operations.
It integrates database management, user interface, OCR processing, and data export capabilities, all organized under a Model–View–Presenter (MVP) architecture.

The main goals are:

Maintain a clean, modular codebase with strong separation of concerns.

Deliver a minimalist and professional UI for operational use.

Provide robust export features (PDF, CSV, backup) for logistics data.

Keep the system efficient, maintainable, and production-ready.

🧩 Current Architecture Overview
📂 Core (sentry/core/)

Contains the functional engine of the system:

export.py → Handles export logic (PDF, CSV, etc.).

ocr.py → Manages OCR recognition pipeline for license plates.

🗄️ Data Layer (sentry/data/)

Implements the Model layer and data management:

database_manager.py / database.py → Connection handling and schema definitions (SQLite).

*_repository.py → Repository pattern for each entity (vehicles, carriers, merchandise, logs).

backup_manager.py → Data backup and restore operations.

base_repository.py → Abstract base for repository operations.

🧠 UI Layer (sentry/ui/)

Implements the Presenter and View layers.

presenters/

auth_presenter.py, vehicle_registration_presenter.py, ocr_camera_presenter.py — Handle logic and communication between data and UI.

views/

base_section_view.py, carrier_view.py, vehicle_registration_view.py, etc. — Define the graphical structure and layout.

Each view follows a sectional design, linked to a corresponding presenter.

The UI is being transitioned into a dashboard layout with top navigation tabs.

widgets/

Custom widgets like dialogs, overlays, and forms (loading_overlay.py, vehicle_form_dialog.py, etc.).

styles/

theme.py defines consistent UI styling (minimalist, neutral color palette).

🧪 Tests (sentry/tests/)

Contains unit and integration tests:

Coverage includes authentication, OCR, dashboard behavior, and repository logic.

Testing framework: pytest.

⚙️ Configuration

config.py defines environment, constants, and paths.

main.py bootstraps the application (entry point).

context.md defines the AI/project context (you’re reading it).

🚀 Improvement Objectives
🧱 1. Architecture & Code Quality

Maintain strict MVP boundaries across all modules.

Improve naming consistency (e.g., snake_case for functions, PascalCase for classes).

Add docstrings and type hints throughout.

Ensure robust error handling and logging in both OCR and database layers.

Refactor repeated logic into core/ or utils/ functions when possible.

Review and clean up unused files or duplicated presenters.

🪟 2. User Interface (UI/UX)

Finalize the dashboard redesign with top navigation tabs.

Simplify user flows for Vehicle, Carrier, and Merchandise registration.

Add consistent iconography and spacing, keeping neutral colors (gray, white, soft blue).

Create a modern but industrial feel, suitable for logistics.

Maintain responsiveness and intuitive placement of actions (e.g., “Scan”, “Export”).

🧾 3. Exports & Reports

Complete the PDF export system (core/export.py):

Include header, company info, timestamp, and formatted data blocks.

Handle exports for Vehicles, Carriers, OCR logs, and Cargo.

Add CSV export for tabular data.

Add visual feedback (e.g., “Export complete”, “File saved to /exports/”).

🧮 4. Data Layer

Review SQLite schema:

vehicles, carriers, merchandise, ocr_records, access_logs.

Ensure referential integrity between entities.

Implement search, filtering, and history tracking features in repositories.

Add automatic backups through backup_manager.py.

🔍 5. OCR & Camera

Improve the pipeline in core/ocr.py:

Support multiple camera sources.

Add real-time preview and detection feedback.

Validate OCR results before storing.

Optimize recognition accuracy through preprocessing and region cropping.

🧭 Guidelines for Cursor AI

Preserve existing folder structure and file naming conventions.

Focus on code clarity, modularity, and stability.

Prioritize UX simplicity and readability in UI updates.

Ensure all changes remain compatible with existing tests.

Prefer Tkinter or PyQt for interface work (depending on what is used).

Keep dependencies minimal and documented.

Follow PEP8 style conventions and type hints.
📂 Expected Folder Structure
sentry/
│
├── core/
│   ├── export.py
│   ├── ocr.py
│
├── data/
│   │   ├── access_log_repository.py
│   │   ├── backup_manager.py
│   │   ├── base_repository.py
│   │   ├── carrier_repository.py
│   │   ├── database_manager.py
        ├── database.py
        ├── merchandise_repository.py
        ├── vehicle_repository.py
│
├── tests/
│   ├── conftest.py
│   ├── test_auth_presenter.py
│   ├── test_auth.py
│   ├── test_dashboard_view.py
│   ├── test_imports.py
│   ├── test_ocr.py
│   ├── test_repositories.py
│   ├── test_vehicle_registration.py
│
├── ui/
├──    presenters/
│   ├── auth_presenter.py
│   ├── ocr_camera_presenter.py
│   ├── vehicle_registration_presenter.py
│├──  styles/
│   ├── theme.py
│├──  views/
│   ├── base_section_view.py
│   ├── base_view.py
│   ├── carrier_registration_view.py
│   ├── carrier_view.py
│   ├── ocr_camera_presenter.py
│   ├── vehicle_registration_presenter.py
│   ├── auth_presenter.py
│   ├── ocr_camera_presenter.py
│   ├── vehicle_registration_presenter.py
│├──  widgets/
│   ├── base_from_dialog.py
│   ├── loading_overlay.py
│   ├── merchandise_from_dialog.py
│   ├── vehicle_form_dialog.py
│   ├── vehicle_query_widget.py
│   ├── main_window.py
├── config.py
├── main.py
└── context.md

💡 Project Vision

sentry.inc should look and feel like a real logistics platform.
Simple, clean, efficient — built for real-world reliability.
The code must reflect strong architecture and professionalism.
Reports should look sharp and export seamlessly.
Everything must work with fluidity and stability.

🧾 Changelog
[Unreleased]
Changed

Reorganized dashboard UI with top navigation

Moved section navigation (Vehicles, Merchandise, Carriers, OCR) to tab bar at top

Added quick action buttons (Scan, Export) to top right

Improved layout consistency and user experience

Removed temp_dashboard_view.py in favor of new organized dashboard_view.py

Added

OCR camera integration for vehicle plate recognition

CSV export functionality for vehicles data

Unit tests for dashboard navigation and features