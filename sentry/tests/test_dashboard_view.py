"""Dashboard view tests."""

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt

from sentry.ui.views.dashboard_view import DashboardView
from sentry.ui.views.vehicles_view import VehiclesView
from sentry.ui.views.merchandise_view import MerchandiseView
from sentry.ui.views.carrier_view import CarrierView
from sentry.ui.views.ocr_camera_view import OCRCameraView

# Register GUI test marker
pytestmark = pytest.mark.gui  # Mark all tests in this module as GUI tests

@pytest.fixture(scope='function')
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def main_window(qapp):
    """Create main window to host the dashboard."""
    window = QMainWindow()
    yield window
    window.close()

@pytest.fixture
def dashboard(qapp, main_window):
    """Create dashboard instance."""
    user_data = {'username': 'test_user', 'role': 'admin'}
    dashboard = DashboardView(user_data)
    main_window.setCentralWidget(dashboard)
    main_window.show()
    return dashboard

def test_dashboard_initial_state(dashboard):
    """Test dashboard initial state."""
    # Check initial tab is vehicles (index 0)
    assert dashboard.tab_bar.currentIndex() == 0
    assert dashboard.stack.currentIndex() == 0
    
    # Check all tabs exist
    assert dashboard.tab_bar.count() == 4
    assert "Veículos" in dashboard.tab_bar.tabText(0)
    assert "Mercadorias" in dashboard.tab_bar.tabText(1)
    assert "Transportadoras" in dashboard.tab_bar.tabText(2)
    assert "OCR" in dashboard.tab_bar.tabText(3)
    
    # Check stacked widget has all views
    assert isinstance(dashboard.stack.widget(0), VehiclesView)
    assert isinstance(dashboard.stack.widget(1), MerchandiseView)
    assert isinstance(dashboard.stack.widget(2), CarrierView)
    assert isinstance(dashboard.stack.widget(3), OCRCameraView)

def test_tab_navigation(dashboard):
    """Test tab switching updates stacked widget."""
    # Switch to each tab and verify stack follows
    for i in range(dashboard.tab_bar.count()):
        dashboard.tab_bar.setCurrentIndex(i)
        assert dashboard.stack.currentIndex() == i

def test_quick_scan_button(dashboard):
    """Test quick scan button switches to OCR view."""
    # Click quick scan
    dashboard._quick_scan()
    
    # Should switch to OCR tab (index 3)
    assert dashboard.tab_bar.currentIndex() == 3
    assert dashboard.stack.currentIndex() == 3
    
    # OCR view should be visible and camera should be starting
    ocr_view = dashboard.stack.currentWidget()
    assert isinstance(ocr_view, OCRCameraView)

def test_export_button(dashboard, monkeypatch):
    """Test export button triggers export on current view."""
    # Mock export_data method
    export_called = False
    def mock_export():
        nonlocal export_called
        export_called = True
    
    # Add mock to vehicles view
    vehicles_view = dashboard.stack.widget(0)
    monkeypatch.setattr(vehicles_view, 'export_data', mock_export)
    
    # Trigger export
    dashboard._export_data()
    
    # Export should have been called
    assert export_called

def test_plate_detection_handling(dashboard, monkeypatch):
    """Test plate detection handling."""
    # Mock repository methods
    def mock_get_by_plate(plate):
        if plate == "ABC1234":
            return {'id': 1, 'plate': 'ABC1234', 'model': 'Test Car', 'status': 'ACTIVE'}
        return None
    
    def mock_create_log(data):
        assert 'vehicle_id' in data
        assert 'detected_plate' in data
        assert 'status' in data
    
    monkeypatch.setattr(dashboard.vehicle_repo, 'get_vehicle_by_plate', mock_get_by_plate)
    monkeypatch.setattr(dashboard.access_repo, 'create', mock_create_log)
    
    # Test authorized plate
    dashboard._handle_plate_detection("ABC1234")
    assert "✅" in dashboard.ocr_view.last_detection.text()
    assert "ACTIVE" in dashboard.ocr_view.last_detection.text()
    
    # Test unauthorized plate
    dashboard._handle_plate_detection("XYZ9876")
    assert "❌" in dashboard.ocr_view.last_detection.text()
    assert "não autorizado" in dashboard.ocr_view.last_detection.text()