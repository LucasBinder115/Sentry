"""Modern UI style definitions for consistent look across the application."""

class Colors:
    """Color palette for the application."""
    
    # Primary colors
    PRIMARY = "#2ecc71"
    PRIMARY_DARK = "#27ae60"
    PRIMARY_LIGHT = "#a8e6cf"
    
    # Secondary colors
    SECONDARY = "#3498db"
    SECONDARY_DARK = "#2980b9"
    SECONDARY_LIGHT = "#bbdefb"
    
    # Accent colors
    ACCENT = "#e74c3c"
    ACCENT_DARK = "#c0392b"
    ACCENT_LIGHT = "#fde8e7"
    
    # Background colors
    BACKGROUND = "#f8f9fa"
    BACKGROUND_DARK = "#e9ecef"
    BACKGROUND_LIGHT = "#ffffff"
    
    # Text colors
    TEXT = "#2c3e50"
    TEXT_LIGHT = "#7f8c8d"
    TEXT_DARK = "#2c3e50"
    
    # Status colors
    SUCCESS = "#2ecc71"
    WARNING = "#f1c40f"
    ERROR = "#e74c3c"
    INFO = "#3498db"

class StyleSheet:
    """Style sheets for common widgets."""
    
    BUTTON_PRIMARY = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY_DARK};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background-color: #bdc3c7;
        }}
    """
    
    BUTTON_SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.SECONDARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {Colors.SECONDARY_DARK};
        }}
    """
    
    BUTTON_DANGER = f"""
        QPushButton {{
            background-color: {Colors.ACCENT};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {Colors.ACCENT_DARK};
        }}
    """
    
    INPUT = f"""
        QLineEdit {{
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 2px solid {Colors.PRIMARY};
            outline: none;
        }}
    """
    
    COMBOBOX = f"""
        QComboBox {{
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
            font-size: 14px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox::down-arrow {{
            image: url(down_arrow.png);
            width: 12px;
            height: 12px;
        }}
    """
    
    TABLE = f"""
        QTableWidget {{
            background-color: white;
            gridline-color: #dee2e6;
            border: none;
            border-radius: 8px;
        }}
        QHeaderView::section {{
            background-color: {Colors.BACKGROUND};
            padding: 8px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            font-weight: bold;
        }}
        QTableWidget::item {{
            padding: 8px;
            border: none;
        }}
        QTableWidget::item:selected {{
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.TEXT_DARK};
        }}
    """
    
    FRAME = f"""
        QFrame {{
            background-color: white;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}
    """
    
    TAB_BAR = f"""
        QTabBar::tab {{
            padding: 8px 16px;
            margin: 4px 2px;
            border: none;
            border-radius: 4px;
            background-color: {Colors.BACKGROUND};
        }}
        QTabBar::tab:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {Colors.BACKGROUND_DARK};
        }}
    """
    
    SCROLL_AREA = """
        QScrollArea {
            border: none;
        }
        QScrollBar:vertical {
            border: none;
            background-color: #f1f1f1;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #c1c1c1;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """

class Fonts:
    """Font definitions for the application."""
    
    TITLE = "font-size: 24px; font-weight: bold;"
    SUBTITLE = "font-size: 18px; font-weight: bold;"
    BODY = "font-size: 14px;"
    SMALL = "font-size: 12px;"
    
    @staticmethod
    def title(color=Colors.TEXT):
        return f"{Fonts.TITLE} color: {color};"
    
    @staticmethod
    def subtitle(color=Colors.TEXT):
        return f"{Fonts.SUBTITLE} color: {color};"
    
    @staticmethod
    def body(color=Colors.TEXT):
        return f"{Fonts.BODY} color: {color};"
    
    @staticmethod
    def small(color=Colors.TEXT_LIGHT):
        return f"{Fonts.SMALL} color: {color};"

class Icons:
    """Unicode icons for the application."""
    
    HOME = "🏠"
    VEHICLE = "🚛"
    MERCHANDISE = "📦"
    CARRIER = "🏢"
    CAMERA = "📸"
    SEARCH = "🔍"
    ADD = "➕"
    EDIT = "✏️"
    DELETE = "🗑️"
    EXPORT = "📊"
    USER = "👤"
    LOCK = "🔒"
    CHECK = "✔️"
    WARNING = "⚠️"
    ERROR = "❌"
    INFO = "ℹ️"