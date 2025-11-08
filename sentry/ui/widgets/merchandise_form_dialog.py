"""Merchandise form dialog for adding/editing merchandise."""

from PyQt5.QtWidgets import QLineEdit, QComboBox, QSpinBox, QTextEdit
from ..widgets.base_form_dialog import BaseFormDialog

class MerchandiseFormDialog(BaseFormDialog):
    """Dialog for adding/editing merchandise."""
    
    def __init__(self, merchandise_data=None, parent=None):
        """Initialize merchandise form."""
        super().__init__("Adicionar Mercadoria" if not merchandise_data else "Editar Mercadoria", parent)
        self.merchandise_data = merchandise_data
        self.setup_fields()
        if merchandise_data:
            self.load_data(merchandise_data)
    
    def setup_fields(self):
        """Setup form fields."""
        # Name field
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Caixa de Papelão")
        self.add_field("Nome", self.name_input, required=True)
        
        # Description field
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Descrição detalhada do item...")
        self.description_input.setMaximumHeight(100)
        self.add_field("Descrição", self.description_input)
        
        # Quantity field
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(0)
        self.quantity_input.setMaximum(999999)
        self.add_field("Quantidade", self.quantity_input)
        
        # Unit field
        self.unit_input = QComboBox()
        self.unit_input.addItems([
            "UNIDADE", "CAIXA", "PACOTE", "KG", "LITRO", 
            "METRO", "PALLET", "CONTAINER"
        ])
        self.unit_input.setEditable(True)
        self.add_field("Unidade", self.unit_input, required=True)
        
        # Status field
        self.status_input = QComboBox()
        self.status_input.addItems(["ATIVO", "INATIVO", "EM FALTA"])
        self.add_field("Status", self.status_input)
    
    def load_data(self, data: dict):
        """Load merchandise data into form."""
        self.set_field_value(self.name_input, data.get('name'))
        self.set_field_value(self.description_input, data.get('description'))
        self.set_field_value(self.quantity_input, data.get('quantity', 0))
        self.set_field_value(self.unit_input, data.get('unit'))
        self.set_field_value(self.status_input, data.get('status'))
        
    def validate(self) -> bool:
        """Validate form data."""
        name = self.name_input.text().strip()
        unit = self.unit_input.currentText().strip()
        
        if not name:
            self.show_error("Nome é obrigatório")
            return False
        
        if not unit:
            self.show_error("Unidade é obrigatória")
            return False
        
        return True
    
    def get_data(self) -> dict:
        """Get form data as dict."""
        return {
            'name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'quantity': self.quantity_input.value(),
            'unit': self.unit_input.currentText().strip(),
            'status': self.status_input.currentText()
        }
    
    def show_error(self, message: str):
        """Show error message."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Erro de Validação", message)
        
    def save_data(self, data: dict):
        """Save merchandise data."""
        from ...data.database.merchandise_repository import MerchandiseRepository
        repo = MerchandiseRepository()
        
        try:
            if self.merchandise_data:  # Editing existing merchandise
                repo.update_merchandise(self.merchandise_data['id'], **data)
            else:  # Creating new merchandise
                repo.create_merchandise(
                    name=data['name'],
                    description=data.get('description'),
                    quantity=data['quantity'],
                    unit=data['unit']
                )
        except Exception as e:
            raise Exception(f"Erro ao salvar mercadoria: {str(e)}")