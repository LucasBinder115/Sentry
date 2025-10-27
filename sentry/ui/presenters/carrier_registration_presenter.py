# sentry/ui/presenters/carrier_registration_presenter.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sentry.core.use_cases.register_carrier import (
    RegisterCarrierUseCase, 
    CarrierRegistrationResult,
    InvalidCarrierDataError,
    DuplicateCNPJError,
    CarrierRegistrationError
)
from sentry.infra.database.repositories.carrier_repo import CarrierRepository
from sentry.core.entities.carrier import Carrier

# Configuração de logging
logger = logging.getLogger(__name__)


class CarrierRegistrationStatus(Enum):
    """Status possíveis do registro de transportadora."""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    DUPLICATE_CNPJ = "duplicate_cnpj"
    SYSTEM_ERROR = "system_error"
    INCOMPLETE_DATA = "incomplete_data"


@dataclass
class CarrierRegistrationRequest:
    """Dados da requisição de registro de transportadora."""
    name: str
    cnpj: str
    responsible_name: Optional[str] = None
    contact_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    operating_regions: Optional[List[str]] = None
    vehicle_types: Optional[List[str]] = None
    capacity_kg: Optional[float] = None
    insurance_value: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class CarrierRegistrationResponse:
    """Resposta do registro de transportadora."""
    success: bool
    status: CarrierRegistrationStatus
    message: str
    carrier_id: Optional[str] = None
    carrier_data: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CarrierSearchCriteria:
    """Critérios para busca de transportadoras."""
    query: Optional[str] = None
    status: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    page: int = 1
    page_size: int = 20


class CarrierRegistrationPresenter:
    """
    Presenter para registro e gerenciamento de transportadoras.
    
    Responsável por:
    - Orquestrar o fluxo de registro de transportadoras
    - Validar dados de entrada
    - Formatadar respostas para a UI
    - Gerenciar buscas e listagens
    """
    
    def __init__(self, view=None):
        self.view = view
        self.carrier_repo = CarrierRepository()
        self.register_use_case = RegisterCarrierUseCase(self.carrier_repo)
        
        logger.info("CarrierRegistrationPresenter inicializado")
    
    def register_carrier(self, request: CarrierRegistrationRequest) -> CarrierRegistrationResponse:
        """
        Registra uma nova transportadora.
        
        Args:
            request: Dados da transportadora a ser registrada
            
        Returns:
            CarrierRegistrationResponse: Resposta formatada para a UI
        """
        logger.info(f"Iniciando registro de transportadora: {request.name}")
        
        try:
            # Validação inicial
            validation_errors = self._validate_carrier_request(request)
            if validation_errors:
                return CarrierRegistrationResponse(
                    success=False,
                    status=CarrierRegistrationStatus.VALIDATION_ERROR,
                    message="Dados de entrada inválidos",
                    validation_errors=validation_errors
                )
            
            # Prepara dados para o use case
            carrier_data = self._prepare_carrier_data(request)
            
            # Executa registro
            result = self.register_use_case.execute(carrier_data)
            
            # Prepara resposta de sucesso
            response = self._prepare_success_response(result)
            
            # Notifica view se disponível
            if self.view:
                self.view.on_carrier_registration_success(response)
            
            logger.info(f"Transportadora registrada com sucesso: {request.name} (ID: {result.carrier_id})")
            
            return response
            
        except InvalidCarrierDataError as e:
            logger.warning(f"Dados inválidos no registro: {e}")
            response = CarrierRegistrationResponse(
                success=False,
                status=CarrierRegistrationStatus.VALIDATION_ERROR,
                message=str(e),
                validation_errors=[str(e)]
            )
            
            if self.view:
                self.view.on_carrier_registration_validation_error(response)
            
            return response
            
        except DuplicateCNPJError as e:
            logger.warning(f"CNPJ duplicado: {e}")
            response = CarrierRegistrationResponse(
                success=False,
                status=CarrierRegistrationStatus.DUPLICATE_CNPJ,
                message=str(e)
            )
            
            if self.view:
                self.view.on_carrier_registration_duplicate_error(response)
            
            return response
            
        except CarrierRegistrationError as e:
            logger.error(f"Erro no registro da transportadora: {e}")
            response = CarrierRegistrationResponse(
                success=False,
                status=CarrierRegistrationStatus.SYSTEM_ERROR,
                message="Erro interno no sistema de registro"
            )
            
            if self.view:
                self.view.on_carrier_registration_system_error(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro inesperado no registro: {e}")
            response = CarrierRegistrationResponse(
                success=False,
                status=CarrierRegistrationStatus.SYSTEM_ERROR,
                message="Ocorreu um erro inesperado no sistema"
            )
            
            if self.view:
                self.view.on_carrier_registration_system_error(response)
            
            return response
    
    def search_carriers(self, criteria: CarrierSearchCriteria) -> Dict[str, Any]:
        """
        Busca transportadoras com base nos critérios fornecidos.
        
        Args:
            criteria: Critérios de busca
            
        Returns:
            Dict com resultados da busca
        """
        logger.info(f"Buscando transportadoras: {criteria.query}")
        
        try:
            # Executa busca
            if criteria.query:
                carriers = self.carrier_repo.search(criteria.query, active_only=True)
            else:
                carriers = self.carrier_repo.find_all(active_only=True)
            
            # Aplica filtros adicionais
            filtered_carriers = self._apply_filters(carriers, criteria)
            
            # Paginação
            paginated_results = self._paginate_results(filtered_carriers, criteria)
            
            # Prepara resposta
            response = {
                'success': True,
                'carriers': [self._format_carrier_for_ui(carrier) for carrier in paginated_results],
                'pagination': {
                    'page': criteria.page,
                    'page_size': criteria.page_size,
                    'total_items': len(filtered_carriers),
                    'total_pages': (len(filtered_carriers) + criteria.page_size - 1) // criteria.page_size
                },
                'search_metadata': {
                    'query': criteria.query,
                    'filters_applied': {
                        'status': criteria.status,
                        'city': criteria.city,
                        'state': criteria.state
                    }
                }
            }
            
            # Notifica view se disponível
            if self.view:
                self.view.on_carrier_search_success(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na busca de transportadoras: {e}")
            
            error_response = {
                'success': False,
                'message': 'Erro na busca de transportadoras',
                'carriers': [],
                'pagination': {
                    'page': criteria.page,
                    'page_size': criteria.page_size,
                    'total_items': 0,
                    'total_pages': 0
                }
            }
            
            if self.view:
                self.view.on_carrier_search_error(error_response)
            
            return error_response
    
    def get_carrier_details(self, carrier_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos de uma transportadora.
        
        Args:
            carrier_id: ID da transportadora
            
        Returns:
            Dict com detalhes da transportadora
        """
        logger.info(f"Obtendo detalhes da transportadora: {carrier_id}")
        
        try:
            carrier = self.carrier_repo.find_by_id(carrier_id)
            
            if not carrier:
                response = {
                    'success': False,
                    'message': 'Transportadora não encontrada'
                }
                
                if self.view:
                    self.view.on_carrier_not_found(response)
                
                return response
            
            # Formata dados para UI
            carrier_data = self._format_carrier_detail_for_ui(carrier)
            
            response = {
                'success': True,
                'carrier': carrier_data
            }
            
            if self.view:
                self.view.on_carrier_details_loaded(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao obter detalhes da transportadora {carrier_id}: {e}")
            
            response = {
                'success': False,
                'message': 'Erro ao carregar detalhes da transportadora'
            }
            
            if self.view:
                self.view.on_carrier_details_error(response)
            
            return response
    
    def update_carrier(self, carrier_id: str, update_data: Dict[str, Any]) -> CarrierRegistrationResponse:
        """
        Atualiza dados de uma transportadora.
        
        Args:
            carrier_id: ID da transportadora
            update_data: Dados a serem atualizados
            
        Returns:
            CarrierRegistrationResponse: Resposta da operação
        """
        logger.info(f"Atualizando transportadora: {carrier_id}")
        
        try:
            # Busca transportadora existente
            carrier = self.carrier_repo.find_by_id(carrier_id)
            if not carrier:
                return CarrierRegistrationResponse(
                    success=False,
                    status=CarrierRegistrationStatus.SYSTEM_ERROR,
                    message="Transportadora não encontrada"
                )
            
            # Atualiza dados
            updated_carrier = self._apply_carrier_updates(carrier, update_data)
            
            # Salva alterações
            saved_carrier = self.carrier_repo.update(updated_carrier)
            
            # Prepara resposta
            response = CarrierRegistrationResponse(
                success=True,
                status=CarrierRegistrationStatus.SUCCESS,
                message="Transportadora atualizada com sucesso",
                carrier_id=saved_carrier.id,
                carrier_data=self._format_carrier_for_ui(saved_carrier)
            )
            
            if self.view:
                self.view.on_carrier_update_success(response)
            
            logger.info(f"Transportadora atualizada: {carrier_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na atualização da transportadora {carrier_id}: {e}")
            
            response = CarrierRegistrationResponse(
                success=False,
                status=CarrierRegistrationStatus.SYSTEM_ERROR,
                message="Erro ao atualizar transportadora"
            )
            
            if self.view:
                self.view.on_carrier_update_error(response)
            
            return response
    
    def delete_carrier(self, carrier_id: str) -> Dict[str, Any]:
        """
        Exclui (soft delete) uma transportadora.
        
        Args:
            carrier_id: ID da transportadora
            
        Returns:
            Dict com resultado da operação
        """
        logger.info(f"Excluindo transportadora: {carrier_id}")
        
        try:
            success = self.carrier_repo.delete(carrier_id)
            
            if success:
                response = {
                    'success': True,
                    'message': 'Transportadora excluída com sucesso'
                }
                
                if self.view:
                    self.view.on_carrier_delete_success(response)
                
                logger.info(f"Transportadora excluída: {carrier_id}")
            else:
                response = {
                    'success': False,
                    'message': 'Transportadora não encontrada'
                }
                
                if self.view:
                    self.view.on_carrier_not_found(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao excluir transportadora {carrier_id}: {e}")
            
            response = {
                'success': False,
                'message': 'Erro ao excluir transportadora'
            }
            
            if self.view:
                self.view.on_carrier_delete_error(response)
            
            return response
    
    def get_carrier_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas das transportadoras.
        
        Returns:
            Dict com estatísticas
        """
        try:
            stats = self.carrier_repo.get_stats()
            
            response = {
                'success': True,
                'stats': stats
            }
            
            if self.view:
                self.view.on_carrier_stats_loaded(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            
            response = {
                'success': False,
                'message': 'Erro ao carregar estatísticas'
            }
            
            if self.view:
                self.view.on_carrier_stats_error(response)
            
            return response
    
    def _validate_carrier_request(self, request: CarrierRegistrationRequest) -> List[str]:
        """
        Valida dados da requisição de registro.
        
        Args:
            request: Dados a serem validados
            
        Returns:
            Lista de erros de validação
        """
        errors = []
        
        # Validação do nome
        if not request.name or len(request.name.strip()) < 3:
            errors.append("Nome deve ter pelo menos 3 caracteres")
        
        if len(request.name) > 255:
            errors.append("Nome não pode exceder 255 caracteres")
        
        # Validação do CNPJ
        if not request.cnpj:
            errors.append("CNPJ é obrigatório")
        else:
            # Validação básica de CNPJ (em produção, usar validador completo)
            cnpj_clean = ''.join(filter(str.isdigit, request.cnpj))
            if len(cnpj_clean) != 14:
                errors.append("CNPJ deve ter 14 dígitos")
        
        # Validação do email (se fornecido)
        if request.email and not self._is_valid_email(request.email):
            errors.append("Email inválido")
        
        # Validação do telefone (se fornecido)
        if request.contact_phone and not self._is_valid_phone(request.contact_phone):
            errors.append("Telefone inválido")
        
        return errors
    
    def _prepare_carrier_data(self, request: CarrierRegistrationRequest) -> Dict[str, Any]:
        """
        Prepara dados para o use case de registro.
        
        Args:
            request: Dados da requisição
            
        Returns:
            Dict formatado para o use case
        """
        data = {
            'name': request.name.strip(),
            'cnpj': request.cnpj
        }
        
        # Campos opcionais
        optional_fields = [
            'responsible_name', 'contact_phone', 'email',
            'operating_regions', 'vehicle_types', 'capacity_kg',
            'insurance_value', 'notes'
        ]
        
        for field in optional_fields:
            value = getattr(request, field)
            if value is not None:
                if isinstance(value, str):
                    data[field] = value.strip()
                else:
                    data[field] = value
        
        # Endereço
        if request.address:
            data['address'] = request.address
        
        return data
    
    def _prepare_success_response(self, result: CarrierRegistrationResult) -> CarrierRegistrationResponse:
        """
        Prepara resposta de sucesso.
        
        Args:
            result: Resultado do use case
            
        Returns:
            CarrierRegistrationResponse formatada
        """
        carrier_data = {
            'id': result.carrier_id,
            'name': result.name,
            'cnpj': result.cnpj,
            'registration_date': result.registration_date.isoformat(),
            'status': result.status,
            'metadata': result.metadata
        }
        
        return CarrierRegistrationResponse(
            success=True,
            status=CarrierRegistrationStatus.SUCCESS,
            message="Transportadora registrada com sucesso",
            carrier_id=result.carrier_id,
            carrier_data=carrier_data,
            metadata={
                'registration_date': result.registration_date.isoformat(),
                'has_address': result.metadata.get('has_address', False),
                'has_contact_info': any([
                    result.metadata.get('responsible_name'),
                    result.metadata.get('contact_phone')
                ])
            }
        )
    
    def _apply_filters(self, carriers: List[Carrier], criteria: CarrierSearchCriteria) -> List[Carrier]:
        """Aplica filtros aos resultados da busca."""
        filtered = carriers
        
        # Filtro por status
        if criteria.status:
            filtered = [c for c in filtered if getattr(c, 'status', 'active') == criteria.status]
        
        # Filtro por cidade
        if criteria.city:
            filtered = [c for c in filtered if getattr(c, 'city', '').lower() == criteria.city.lower()]
        
        # Filtro por estado
        if criteria.state:
            filtered = [c for c in filtered if getattr(c, 'state', '').upper() == criteria.state.upper()]
        
        return filtered
    
    def _paginate_results(self, carriers: List[Carrier], criteria: CarrierSearchCriteria) -> List[Carrier]:
        """Aplica paginação aos resultados."""
        start_idx = (criteria.page - 1) * criteria.page_size
        end_idx = start_idx + criteria.page_size
        return carriers[start_idx:end_idx]
    
    def _format_carrier_for_ui(self, carrier: Carrier) -> Dict[str, Any]:
        """Formata dados da transportadora para a UI."""
        return {
            'id': carrier.id,
            'name': carrier.name,
            'cnpj': carrier.cnpj,
            'responsible_name': getattr(carrier, 'responsible_name', None),
            'contact_phone': getattr(carrier, 'contact_phone', None),
            'email': getattr(carrier, 'email', None),
            'city': getattr(carrier, 'city', None),
            'state': getattr(carrier, 'state', None),
            'status': getattr(carrier, 'status', 'active'),
            'vehicle_count': getattr(carrier, 'vehicle_count', 0),  # Seria calculado
            'created_at': getattr(carrier, 'created_at', datetime.now()).isoformat()
        }
    
    def _format_carrier_detail_for_ui(self, carrier: Carrier) -> Dict[str, Any]:
        """Formata dados detalhados da transportadora para a UI."""
        base_data = self._format_carrier_for_ui(carrier)
        
        # Adiciona campos detalhados
        detail_data = {
            'address': getattr(carrier, 'address', {}),
            'operating_regions': getattr(carrier, 'operating_regions', []),
            'vehicle_types': getattr(carrier, 'vehicle_types', []),
            'capacity_kg': getattr(carrier, 'capacity_kg', None),
            'insurance_value': getattr(carrier, 'insurance_value', None),
            'notes': getattr(carrier, 'notes', None),
            'updated_at': getattr(carrier, 'updated_at', datetime.now()).isoformat()
        }
        
        base_data.update(detail_data)
        return base_data
    
    def _apply_carrier_updates(self, carrier: Carrier, update_data: Dict[str, Any]) -> Carrier:
        """Aplica atualizações a uma transportadora existente."""
        for field, value in update_data.items():
            if hasattr(carrier, field) and value is not None:
                setattr(carrier, field, value)
        
        # Atualiza timestamp
        carrier.updated_at = datetime.now()
        
        return carrier
    
    def _is_valid_email(self, email: str) -> bool:
        """Valida formato de email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Valida formato de telefone brasileiro."""
        import re
        # Remove caracteres não numéricos
        clean_phone = ''.join(filter(str.isdigit, phone))
        return 10 <= len(clean_phone) <= 11
    
    def cleanup(self):
        """Libera recursos."""
        try:
            if hasattr(self.carrier_repo, 'close'):
                self.carrier_repo.close()
            logger.info("CarrierRegistrationPresenter - recursos liberados")
        except Exception as e:
            logger.error(f"Erro no cleanup do CarrierRegistrationPresenter: {e}")


# Interface para a View
class CarrierRegistrationViewInterface:
    """Interface que a View deve implementar."""
    
    def on_carrier_registration_success(self, response: CarrierRegistrationResponse):
        """Chamado quando registro é bem-sucedido."""
        pass
    
    def on_carrier_registration_validation_error(self, response: CarrierRegistrationResponse):
        """Chamado quando há erro de validação."""
        pass
    
    def on_carrier_registration_duplicate_error(self, response: CarrierRegistrationResponse):
        """Chamado quando CNPJ já existe."""
        pass
    
    def on_carrier_registration_system_error(self, response: CarrierRegistrationResponse):
        """Chamado quando há erro de sistema."""
        pass
    
    def on_carrier_search_success(self, response: Dict[str, Any]):
        """Chamado quando busca é bem-sucedida."""
        pass
    
    def on_carrier_search_error(self, response: Dict[str, Any]):
        """Chamado quando há erro na busca."""
        pass
    
    def on_carrier_details_loaded(self, response: Dict[str, Any]):
        """Chamado quando detalhes são carregados."""
        pass
    
    def on_carrier_details_error(self, response: Dict[str, Any]):
        """Chamado quando há erro ao carregar detalhes."""
        pass
    
    def on_carrier_not_found(self, response: Dict[str, Any]):
        """Chamado quando transportadora não é encontrada."""
        pass
    
    def on_carrier_update_success(self, response: CarrierRegistrationResponse):
        """Chamado quando atualização é bem-sucedida."""
        pass
    
    def on_carrier_update_error(self, response: CarrierRegistrationResponse):
        """Chamado quando há erro na atualização."""
        pass
    
    def on_carrier_delete_success(self, response: Dict[str, Any]):
        """Chamado quando exclusão é bem-sucedida."""
        pass
    
    def on_carrier_delete_error(self, response: Dict[str, Any]):
        """Chamado quando há erro na exclusão."""
        pass
    
    def on_carrier_stats_loaded(self, response: Dict[str, Any]):
        """Chamado quando estatísticas são carregadas."""
        pass
    
    def on_carrier_stats_error(self, response: Dict[str, Any]):
        """Chamado quando há erro ao carregar estatísticas."""
        pass


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # View de exemplo para demonstração
    class ExampleCarrierView(CarrierRegistrationViewInterface):
        def on_carrier_registration_success(self, response):
            print(f"✅ Transportadora registrada: {response.carrier_data['name']}")
            print(f"📋 ID: {response.carrier_id}")
        
        def on_carrier_registration_validation_error(self, response):
            print(f"❌ Erro de validação: {response.message}")
            for error in response.validation_errors:
                print(f"   - {error}")
        
        def on_carrier_search_success(self, response):
            print(f"🔍 Busca concluída: {len(response['carriers'])} transportadoras encontradas")
    
    # Teste do presenter
    try:
        view = ExampleCarrierView()
        presenter = CarrierRegistrationPresenter(view=view)
        
        # Simula registro
        registration_request = CarrierRegistrationRequest(
            name="Transportadora Expresso Brasil LTDA",
            cnpj="12.345.678/0001-95",
            responsible_name="João Silva",
            contact_phone="(11) 99999-9999",
            email="contato@expressobrasil.com.br",
            address={
                'street': 'Rua das Flores',
                'number': '123',
                'complement': 'Sala 45',
                'neighborhood': 'Centro',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01234-567'
            }
        )
        
        response = presenter.register_carrier(registration_request)
        print(f"Resultado do registro: {response.success} - {response.message}")
        
        # Teste de busca
        search_criteria = CarrierSearchCriteria(
            query="Expresso",
            page=1,
            page_size=10
        )
        
        search_results = presenter.search_carriers(search_criteria)
        print(f"Resultado da busca: {search_results['success']}")
        
        # Cleanup
        presenter.cleanup()
        
    except Exception as e:
        print(f"❌ Erro no exemplo: {e}")