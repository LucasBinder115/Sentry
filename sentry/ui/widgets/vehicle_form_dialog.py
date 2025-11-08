"""Vehicle form dialog for adding/editing vehicles."""

from PyQt5.QtWidgets import QLineEdit, QComboBox
from .base_form_dialog import BaseFormDialog

class VehicleFormDialog(BaseFormDialog):
    """Dialog for adding/editing vehicles."""
    
    def __init__(self, vehicle_data=None, parent=None):
        """Initialize vehicle form."""
        super().__init__("Adicionar Veículo" if not vehicle_data else "Editar Veículo", parent)
        self.vehicle_data = vehicle_data
        self.setup_fields()
        if vehicle_data:
            self.load_data(vehicle_data)
    
    def setup_fields(self):
        """Setup form fields."""
        # Plate field
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("ABC1234")
        self.plate_input.setMaxLength(7)
        self.add_field("Placa", self.plate_input, required=True)
        
        # Model field
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Ex: Volvo FH 540")
        self.add_field("Modelo", self.model_input, required=True)
        
        # Color field
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Ex: Branco")
        self.add_field("Cor", self.color_input)
        
        # Status field
        self.status_input = QComboBox()
        self.status_input.addItems(["ATIVO", "INATIVO", "MANUTENÇÃO"])
        self.add_field("Status", self.status_input)
    
    def load_data(self, data: dict):
        """Load vehicle data into form."""
        self.set_field_value(self.plate_input, data.get('plate'))
        self.set_field_value(self.model_input, data.get('model'))
        self.set_field_value(self.color_input, data.get('color'))
        self.set_field_value(self.status_input, data.get('status'))
        
        # Disable plate editing for existing vehicles
        self.plate_input.setReadOnly(True)
    
    def validate(self) -> bool:
        """Validate form data."""
        plate = self.plate_input.text().strip()
        model = self.model_input.text().strip()
        
        if not plate:
            self.show_error("Placa é obrigatória")
            return False
        
        if not model:
            self.show_error("Modelo é obrigatório")
            return False
        
        # Validate plate format (ABC1234)
        if not (len(plate) == 7 and
                plate[:3].isalpha() and
                plate[3:].isdigit()):
            self.show_error("Placa inválida. Use o formato ABC1234")
            return False
        
        return True
    
    def get_data(self) -> dict:
        """Get form data as dict."""
        return {
            'plate': self.plate_input.text().strip().upper(),
            'model': self.model_input.text().strip(),
            'color': self.color_input.text().strip(),
            'status': self.status_input.currentText()
        }
    
    def show_error(self, message: str):
        """Show error message."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Erro de Validação", message)
        
    def save_data(self, data: dict):
        """Save vehicle data."""
        from ...data.database.vehicle_repository import VehicleRepository
        repo = VehicleRepository()
        
        try:
            if self.vehicle_data:  # Editing existing vehicle
                repo.update_vehicle(self.vehicle_data['id'], **data)
            else:  # Creating new vehicle
                repo.create_vehicle(
                    plate=data['plate'],
                    model=data['model'],
                    color=data.get('color')
                )
        except Exception as e:
            raise Exception(f"Erro ao salvar veículo: {str(e)}")