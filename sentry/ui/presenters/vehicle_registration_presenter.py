"""Vehicle registration presenter implementation."""

import logging
from typing import Dict, Any

from ..views.vehicle_registration_view import VehicleRegistrationView
from ...data.database.vehicle_repository import VehicleRepository

class VehicleRegistrationPresenter:
    """Presenter for vehicle registration handling."""

    def __init__(self, view: VehicleRegistrationView):
        """Initialize the presenter."""
        self.view = view
        self.repository = VehicleRepository()
        self.logger = logging.getLogger(__name__)
        self._connect_signals()

    def _connect_signals(self):
        """Connect view signals to presenter methods."""
        if hasattr(self.view, 'registration_successful'):
            self.view.registration_successful.connect(self._on_register_vehicle)

    def _on_register_vehicle(self, vehicle_data: Dict[str, Any]):
        """Handle vehicle registration."""
        try:
            # Create vehicle in database
            vehicle = self.repository.create_vehicle(
                plate=vehicle_data['plate'],
                model=vehicle_data['model'],
                color=vehicle_data.get('color')
            )

            # Show success message
            self.view.show_success(f"Veículo {vehicle['plate']} cadastrado com sucesso!")
            
            # Clear the form
            self.view.clear_form()

        except ValueError as e:
            self.view.show_error(str(e))
        except Exception as e:
            self.logger.error(f"Error registering vehicle: {e}")
            self.view.show_error("Erro ao cadastrar veículo. Tente novamente.")

def create_vehicle_presenter(view: VehicleRegistrationView) -> VehicleRegistrationPresenter:
    """Factory function to create a vehicle registration presenter."""
    return VehicleRegistrationPresenter(view)
