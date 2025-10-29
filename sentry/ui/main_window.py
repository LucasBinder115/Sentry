"""Main window implementation."""

from PyQt5.QtWidgets import QMainWindow, QWidget, QStackedWidget
from PyQt5.QtCore import Qt
from typing import Optional, Dict, Any

from .views.login_view import LoginView
from .views.dashboard_view import DashboardView
from .presenters.auth_presenter import AuthPresenter

class MainWindow(QMainWindow):
    """Main application window managing all views."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # Window setup
        self.setWindowTitle("SENTRY")
        self.setMinimumSize(1024, 768)
        
        # Initialize state
        self.current_user: Optional[Dict[str, Any]] = None
        
        # Create view stack
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create views
        self.login_view = LoginView()
        self.dashboard_view: Optional[DashboardView] = None
        
        # Setup auth presenter
        self.auth_presenter = AuthPresenter(self.login_view)
        
        # Add login view to stack
        self.stack.addWidget(self.login_view)
        
        # Connect signals
        self.login_view.login_attempt.connect(self.handle_login)
        
    def handle_login(self, credentials: Dict[str, str]):
        """Handle login attempt."""
        user_data = self.auth_presenter.login(
            credentials['username'],
            credentials['password']
        )
        
        if user_data:
            self.current_user = user_data
            self.show_dashboard()
        else:
            self.login_view.show_error("Login inválido")
    
    def show_dashboard(self):
        """Initialize and show dashboard view."""
        # Create new dashboard instance if needed
        if not self.dashboard_view:
            self.dashboard_view = DashboardView(self.current_user)
            self.dashboard_view.logout.connect(self.handle_logout)
            self.stack.addWidget(self.dashboard_view)
        
        # Switch to dashboard view
        self.stack.setCurrentWidget(self.dashboard_view)
        
        # Update window settings for dashboard
        self.setMinimumSize(1280, 800)
        self.showMaximized()
    
    def handle_logout(self):
        """Handle logout request."""
        if self.auth_presenter.logout():
            # Clear current user
            self.current_user = None
            
            # Remove and delete dashboard
            if self.dashboard_view:
                self.stack.removeWidget(self.dashboard_view)
                self.dashboard_view.deleteLater()
                self.dashboard_view = None
            
            # Show login view
            self.stack.setCurrentWidget(self.login_view)
            
            # Reset window settings
            self.setMinimumSize(1024, 768)
            self.showNormal()