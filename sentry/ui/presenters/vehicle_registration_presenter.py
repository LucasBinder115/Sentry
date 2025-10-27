# sentry/ui/presenters/vehicle_registration_presenter.py

import re
from datetime import datetime
from typing import Dict, List, Optional, Any

# ====================================================================
# Imports com Fallbacks Robustos
# ====================================================================
try:
    from sentry.core.use_cases.register_vehicle import RegisterVehicleUseCase
except ImportError:
    # Fallback para desenvolvimento
    class RegisterVehicleUseCase:
        def __init__(self, vehicle_repo):
            self.vehicle_repo = vehicle_repo
        
        def execute(self, vehicle_data):
            # Simula registro bem-sucedido
            vehicle_data['id'] = 1
            vehicle_data['created_at'] = datetime.now()
            vehicle_data['status'] = 'active'
            return vehicle_data

try:
    from sentry.infra.database.repositories.vehicle_repo import VehicleRepository
except ImportError:
    class VehicleRepository:
        def save(self, vehicle_data):
            # Simula salvamento no banco
            vehicle_data['id'] = 1
            return vehicle_data
        
        def find_by_plate(self, plate):
            return None  # Simula placa não existente
        
        def find_all(self):
            return []

try:
    from sentry.core.entities.vehicle import Vehicle
except ImportError:
    class Vehicle:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

try:
    from sentry.core.entities.carrier import Carrier
except ImportError:
    class Carrier:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


class VehicleRegistrationPresenter:
    """
    Presenter para registro de veículos.
    Gerencia a comunicação entre a view de registro e os casos de uso.
    """
    
    # Tipos de veículo suportados
    VEHICLE_TYPES = [
        "Caminhão", "Carreta", "Bitrem", "Rodotrem", "VUC", "Toco",
        "Caminhão Baú", "Caminhão Caçamba", "Caminhão Tanque", "Van", "Utilitário"
    ]
    
    # Categorias de eixo
    AXLE_CATEGORIES = ["2 Eixos", "3 Eixos", "4 Eixos", "5 Eixos", "6 Eixos", "7+ Eixos"]
    
    # Combustíveis
    FUEL_TYPES = ["Diesel", "Gasolina", "Etanol", "Flex", "GNV", "Elétrico", "Híbrido"]

    def __init__(self, view):
        self.view = view
        self._initialize_dependencies()
        self._setup_validation_rules()
        
        # Estado do presenter
        self.current_vehicle = None
        self.registration_history = []
        self.validation_errors = []
        self.carrier_cache = {}

    def _initialize_dependencies(self):
        """Inicializa dependências com tratamento robusto de erros."""
        try:
            self.vehicle_repo = VehicleRepository()
            self.register_use_case = RegisterVehicleUseCase(self.vehicle_repo)
        except Exception as e:
            self._handle_dependency_error(e)

    def _handle_dependency_error(self, error):
        """Trata erros de inicialização de dependências."""
        error_msg = f"Erro na inicialização: {error}"
        print(f"AVISO: {error_msg}")
        
        # Cria instâncias fallback
        self.vehicle_repo = VehicleRepository()
        self.register_use_case = RegisterVehicleUseCase(self.vehicle_repo)
        
        self.view.show_warning("Algumas funcionalidades podem estar limitadas (modo de desenvolvimento)")

    def _setup_validation_rules(self):
        """Configura regras de validação para dados do veículo."""
        self.validation_rules = {
            'plate': {
                'required': True,
                'patterns': [
                    r'^[A-Z]{3}\d{1}[A-Z]{1}\d{2}$',  # Mercosul
                    r'^[A-Z]{3}\d{4}$'               # Modelo antigo
                ]
            },
            'model': {
                'required': True,
                'min_length': 2,
                'max_length': 50
            },
            'vehicle_type': {
                'required': True,
                'allowed_values': self.VEHICLE_TYPES
            },
            'brand': {
                'required': True,
                'min_length': 2,
                'max_length': 30
            },
            'color': {
                'required': False,
                'max_length': 20
            },
            'manufacture_year': {
                'required': True,
                'min_value': 1950,
                'max_value': datetime.now().year + 1
            },
            'model_year': {
                'required': True,
                'min_value': 1950,
                'max_value': datetime.now().year + 1
            },
            'chassis': {
                'required': False,
                'min_length': 10,
                'max_length': 30
            },
            'renavam': {
                'required': False,
                'exact_length': 11
            }
        }

    # ====================================================================
    # MÉTODOS PRINCIPAIS DE REGISTRO
    # ====================================================================

    def register_vehicle(self, vehicle_data: Dict[str, Any]):
        """
        Registra um novo veículo no sistema.
        
        Args:
            vehicle_data: Dicionário com dados do veículo
                - plate: placa do veículo (obrigatório)
                - model: modelo do veículo (obrigatório)
                - vehicle_type: tipo de veículo (obrigatório)
                - brand: marca (obrigatório)
                - color: cor (opcional)
                - manufacture_year: ano de fabricação (obrigatório)
                - model_year: ano do modelo (obrigatório)
                - chassis: número do chassi (opcional)
                - renavam: número do RENAVAM (opcional)
                - carrier_id: ID do transportador (opcional)
                - axle_configuration: configuração de eixos (opcional)
                - fuel_type: tipo de combustível (opcional)
                - capacity: capacidade de carga (opcional)
        """
        try:
            # Limpa erros anteriores
            self.validation_errors.clear()
            
            # Valida dados básicos
            if not self._validate_required_fields(vehicle_data):
                return
            
            # Validações específicas
            if not self._perform_comprehensive_validation(vehicle_data):
                return
            
            # Verifica se placa já existe
            if not self._check_plate_availability(vehicle_data['plate']):
                return
            
            # Prepara dados para registro
            processed_data = self._prepare_vehicle_data(vehicle_data)
            
            # Configura estado de loading
            self.view.set_loading(True)
            self.view.show_info("Registrando veículo...")
            
            # Executa registro
            result = self.register_use_case.execute(processed_data)
            
            # Processa resultado
            self._handle_registration_success(result, processed_data)
            
        except ValueError as e:
            self._handle_registration_error(f"Dados inválidos: {e}")
        except Exception as e:
            self._handle_registration_error(f"Erro inesperado durante registro: {e}")
        finally:
            self.view.set_loading(False)

    def _validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """Valida campos obrigatórios."""
        required_fields = ['plate', 'model', 'vehicle_type', 'brand', 'manufacture_year', 'model_year']
        missing_fields = []
        
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Campos obrigatórios não preenchidos: {', '.join(missing_fields)}"
            self.view.show_error(error_msg)
            return False
        
        return True

    def _perform_comprehensive_validation(self, data: Dict[str, Any]) -> bool:
        """Executa validação abrangente dos dados."""
        validations = [
            self._validate_plate(data.get('plate', '')),
            self._validate_model(data.get('model', '')),
            self._validate_vehicle_type(data.get('vehicle_type', '')),
            self._validate_brand(data.get('brand', '')),
            self._validate_color(data.get('color')),
            self._validate_manufacture_year(data.get('manufacture_year')),
            self._validate_model_year(data.get('model_year')),
            self._validate_chassis(data.get('chassis')),
            self._validate_renavam(data.get('renavam')),
            self._validate_years_consistency(data.get('manufacture_year'), data.get('model_year'))
        ]
        
        return all(validations)

    def _validate_plate(self, plate: str) -> bool:
        """Valida placa do veículo."""
        if not plate:
            self.validation_errors.append("Placa é obrigatória")
            return False
        
        # Remove caracteres especiais e converte para maiúsculas
        cleaned_plate = re.sub(r'[^a-zA-Z0-9]', '', plate).upper()
        
        # Verifica padrões
        patterns = self.validation_rules['plate']['patterns']
        is_valid = any(re.match(pattern, cleaned_plate) for pattern in patterns)
        
        if not is_valid:
            self.validation_errors.append(
                "Placa inválida. Formatos aceitos: \n"
                "• Mercosul: AAA1A11 \n"
                "• Modelo Antigo: AAA1111"
            )
            return False
        
        return True

    def _validate_model(self, model: str) -> bool:
        """Valida modelo do veículo."""
        rules = self.validation_rules['model']
        
        if not model:
            self.validation_errors.append("Modelo é obrigatório")
            return False
        
        if len(model) < rules['min_length']:
            self.validation_errors.append(f"Modelo muito curto (mínimo {rules['min_length']} caracteres)")
            return False
        
        if len(model) > rules['max_length']:
            self.validation_errors.append(f"Modelo muito longo (máximo {rules['max_length']} caracteres)")
            return False
        
        return True

    def _validate_vehicle_type(self, vehicle_type: str) -> bool:
        """Valida tipo de veículo."""
        if not vehicle_type:
            self.validation_errors.append("Tipo de veículo é obrigatório")
            return False
        
        if vehicle_type not in self.validation_rules['vehicle_type']['allowed_values']:
            allowed = ", ".join(self.validation_rules['vehicle_type']['allowed_values'])
            self.validation_errors.append(f"Tipo de veículo inválido. Use: {allowed}")
            return False
        
        return True

    def _validate_brand(self, brand: str) -> bool:
        """Valida marca do veículo."""
        rules = self.validation_rules['brand']
        
        if not brand:
            self.validation_errors.append("Marca é obrigatória")
            return False
        
        if len(brand) < rules['min_length']:
            self.validation_errors.append(f"Marca muito curta (mínimo {rules['min_length']} caracteres)")
            return False
        
        if len(brand) > rules['max_length']:
            self.validation_errors.append(f"Marca muito longa (máximo {rules['max_length']} caracteres)")
            return False
        
        return True

    def _validate_color(self, color: str) -> bool:
        """Valida cor do veículo."""
        if not color:
            return True  # Opcional
        
        rules = self.validation_rules['color']
        
        if len(color) > rules['max_length']:
            self.validation_errors.append(f"Cor muito longa (máximo {rules['max_length']} caracteres)")
            return False
        
        return True

    def _validate_manufacture_year(self, year) -> bool:
        """Valida ano de fabricação."""
        return self._validate_year_field(year, "ano de fabricação")

    def _validate_model_year(self, year) -> bool:
        """Valida ano do modelo."""
        return self._validate_year_field(year, "ano do modelo")

    def _validate_year_field(self, year, field_name: str) -> bool:
        """Valida campo de ano."""
        if not year:
            self.validation_errors.append(f"{field_name.capitalize()} é obrigatório")
            return False
        
        try:
            year_int = int(year)
            rules = self.validation_rules['manufacture_year']
            
            if year_int < rules['min_value']:
                self.validation_errors.append(f"{field_name.capitalize()} não pode ser anterior a {rules['min_value']}")
                return False
            
            if year_int > rules['max_value']:
                self.validation_errors.append(f"{field_name.capitalize()} não pode ser posterior a {rules['max_value']}")
                return False
            
            return True
            
        except (TypeError, ValueError):
            self.validation_errors.append(f"{field_name.capitalize()} deve ser um número válido")
            return False

    def _validate_years_consistency(self, manufacture_year, model_year) -> bool:
        """Valida consistência entre anos de fabricação e modelo."""
        try:
            manufacture = int(manufacture_year)
            model = int(model_year)
            
            if model < manufacture:
                self.validation_errors.append("Ano do modelo não pode ser anterior ao ano de fabricação")
                return False
            
            return True
            
        except (TypeError, ValueError):
            return True  # Já validado individualmente

    def _validate_chassis(self, chassis: str) -> bool:
        """Valida número do chassi."""
        if not chassis:
            return True  # Opcional
        
        rules = self.validation_rules['chassis']
        
        if len(chassis) < rules['min_length']:
            self.validation_errors.append(f"Chassi muito curto (mínimo {rules['min_length']} caracteres)")
            return False
        
        if len(chassis) > rules['max_length']:
            self.validation_errors.append(f"Chassi muito longo (máximo {rules['max_length']} caracteres)")
            return False
        
        return True

    def _validate_renavam(self, renavam: str) -> bool:
        """Valida número do RENAVAM."""
        if not renavam:
            return True  # Opcional
        
        rules = self.validation_rules['renavam']
        
        if len(renavam) != rules['exact_length']:
            self.validation_errors.append(f"RENAVAM deve ter exatamente {rules['exact_length']} dígitos")
            return False
        
        if not renavam.isdigit():
            self.validation_errors.append("RENAVAM deve conter apenas números")
            return False
        
        return True

    def _check_plate_availability(self, plate: str) -> bool:
        """Verifica se a placa já está cadastrada."""
        try:
            # Remove caracteres especiais para busca
            cleaned_plate = re.sub(r'[^a-zA-Z0-9]', '', plate).upper()
            
            existing_vehicle = self.vehicle_repo.find_by_plate(cleaned_plate)
            if existing_vehicle:
                self.validation_errors.append(f"Placa {cleaned_plate} já está cadastrada no sistema")
                return False
            
            return True
            
        except Exception as e:
            print(f"Aviso: Não foi possível verificar disponibilidade da placa: {e}")
            return True  # Permite continuar em caso de erro na verificação

    def _prepare_vehicle_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara e enriquece os dados do veículo."""
        processed_data = data.copy()
        
        # Padroniza placa
        if 'plate' in processed_data:
            processed_data['plate'] = re.sub(r'[^a-zA-Z0-9]', '', processed_data['plate']).upper()
        
        # Adiciona metadados
        processed_data['registered_at'] = datetime.now()
        processed_data['status'] = 'active'
        processed_data['last_updated'] = datetime.now()
        
        # Converte anos para inteiros
        if 'manufacture_year' in processed_data:
            processed_data['manufacture_year'] = int(processed_data['manufacture_year'])
        
        if 'model_year' in processed_data:
            processed_data['model_year'] = int(processed_data['model_year'])
        
        # Normaliza strings
        string_fields = ['model', 'brand', 'color', 'vehicle_type']
        for field in string_fields:
            if field in processed_data and processed_data[field]:
                processed_data[field] = processed_data[field].strip().upper()
        
        return processed_data

    def _handle_registration_success(self, result: Dict[str, Any], original_data: Dict[str, Any]):
        """Processa registro bem-sucedido."""
        # Adiciona ao histórico
        registration_record = {
            'id': result.get('id', len(self.registration_history) + 1),
            'plate': original_data.get('plate'),
            'model': original_data.get('model'),
            'brand': original_data.get('brand'),
            'vehicle_type': original_data.get('vehicle_type'),
            'registered_at': datetime.now(),
            'data': original_data
        }
        
        self.registration_history.append(registration_record)
        
        # Limita histórico
        if len(self.registration_history) > 100:
            self.registration_history = self.registration_history[-100:]
        
        # Prepara mensagem de sucesso
        success_message = self._format_success_message(registration_record)
        
        # Notifica view
        self.view.show_success(success_message)
        self.view.clear_form()
        
        # Atualiza lista de veículos se necessário
        if hasattr(self.view, 'refresh_vehicle_list'):
            self.view.refresh_vehicle_list()

    def _handle_registration_error(self, error_message: str):
        """Processa erro durante registro."""
        # Adiciona erros de validação se houver
        if self.validation_errors:
            full_error = f"{error_message}\n• " + "\n• ".join(self.validation_errors)
            self.view.show_error(full_error)
        else:
            self.view.show_error(error_message)
        
        # Mantém os dados no formulário para correção
        self.view.preserve_form_data()

    def _format_success_message(self, record: Dict[str, Any]) -> str:
        """Formata mensagem de sucesso para exibição."""
        return f"""
✅ Veículo registrado com sucesso!

🚗 Placa: {record['plate']}
🏷️ Modelo: {record['model']} 
🏭 Marca: {record['brand']}
📋 Tipo: {record['vehicle_type']}
🆔 ID: {record['id']}
⏰ Registrado em: {record['registered_at'].strftime('%d/%m/%Y %H:%M')}
        """.strip()

    # ====================================================================
    # MÉTODOS AVANÇADOS DE REGISTRO
    # ====================================================================

    def batch_register_vehicles(self, vehicle_list: List[Dict[str, Any]]):
        """Registra múltiplos veículos em lote."""
        results = {
            'successful': [],
            'failed': []
        }
        
        total = len(vehicle_list)
        
        for index, vehicle_data in enumerate(vehicle_list, 1):
            try:
                self.view.show_info(f"Processando {index} de {total}...")
                
                # Validação individual
                self.validation_errors.clear()
                if not self._perform_comprehensive_validation(vehicle_data):
                    results['failed'].append({
                        'data': vehicle_data,
                        'error': " | ".join(self.validation_errors)
                    })
                    continue
                
                # Verifica placa
                if not self._check_plate_availability(vehicle_data['plate']):
                    results['failed'].append({
                        'data': vehicle_data,
                        'error': "Placa já existe"
                    })
                    continue
                
                # Registro individual
                processed_data = self._prepare_vehicle_data(vehicle_data)
                result = self.register_use_case.execute(processed_data)
                
                results['successful'].append({
                    'data': vehicle_data,
                    'result': result
                })
                
            except Exception as e:
                results['failed'].append({
                    'data': vehicle_data,
                    'error': str(e)
                })
        
        # Relatório final
        self._show_batch_report(results)

    def _show_batch_report(self, results: Dict[str, List]):
        """Exibe relatório de registro em lote."""
        successful_count = len(results['successful'])
        failed_count = len(results['failed'])
        
        report_message = f"""
📊 Relatório de Registro em Lote:

✅ Sucessos: {successful_count}
❌ Falhas: {failed_count}
📋 Total processado: {successful_count + failed_count}
        """
        
        if failed_count > 0:
            report_message += f"\n⚠️ {failed_count} registro(s) falharam. Verifique os dados."
        
        self.view.show_info(report_message.strip())

    def validate_vehicle_data(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida dados do veículo sem registrar.
        Retorna dict com resultados da validação.
        """
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        try:
            # Validações básicas
            self.validation_errors.clear()
            is_valid = self._perform_comprehensive_validation(vehicle_data)
            
            validation_result['is_valid'] = is_valid
            validation_result['errors'] = self.validation_errors.copy()
            
            # Adiciona avisos e sugestões
            validation_result['warnings'] = self._generate_warnings(vehicle_data)
            validation_result['suggestions'] = self._generate_suggestions(vehicle_data)
            
        except Exception as e:
            validation_result['errors'].append(f"Erro na validação: {e}")
        
        return validation_result

    def _generate_warnings(self, data: Dict[str, Any]) -> List[str]:
        """Gera avisos sobre os dados do veículo."""
        warnings = []
        
        # Verifica anos muito antigos
        manufacture_year = data.get('manufacture_year')
        if manufacture_year:
            try:
                year = int(manufacture_year)
                current_year = datetime.now().year
                if current_year - year > 30:
                    warnings.append("Veículo muito antigo - verifique documentação e estado de conservação")
            except (TypeError, ValueError):
                pass
        
        # Verifica tipo de veículo vs capacidade
        vehicle_type = data.get('vehicle_type', '')
        capacity = data.get('capacity')
        
        if capacity and 'CAMINHÃO' in vehicle_type.upper() and capacity < 5000:
            warnings.append("Capacidade muito baixa para caminhão - verifique se está correto")
        
        return warnings

    def _generate_suggestions(self, data: Dict[str, Any]) -> List[str]:
        """Gera sugestões para melhorar os dados."""
        suggestions = []
        
        vehicle_type = data.get('vehicle_type', '')
        brand = data.get('brand', '').upper()
        
        # Sugere combustível baseado no tipo de veículo
        if not data.get('fuel_type'):
            if 'CAMINHÃO' in vehicle_type.upper():
                suggestions.append("Sugerimos combustível 'Diesel' para caminhões")
            elif 'VAN' in vehicle_type.upper() or 'UTILITÁRIO' in vehicle_type.upper():
                suggestions.append("Sugerimos combustível 'Flex' para vans e utilitários")
        
        # Sugere configuração de eixos
        if not data.get('axle_configuration'):
            if 'RODOTREM' in vehicle_type.upper() or 'BITREM' in vehicle_type.upper():
                suggestions.append("Sugerimos configuração de '7+ Eixos' para carretas especiais")
            elif 'CARRETA' in vehicle_type.upper():
                suggestions.append("Sugerimos configuração de '6 Eixos' para carretas")
        
        return suggestions

    # ====================================================================
    # MÉTODOS UTILITÁRIOS
    # ====================================================================

    def get_vehicle_types(self) -> List[str]:
        """Retorna lista de tipos de veículo disponíveis."""
        return self.VEHICLE_TYPES.copy()

    def get_axle_categories(self) -> List[str]:
        """Retorna lista de categorias de eixo."""
        return self.AXLE_CATEGORIES.copy()

    def get_fuel_types(self) -> List[str]:
        """Retorna lista de tipos de combustível."""
        return self.FUEL_TYPES.copy()

    def get_registration_history(self) -> List[Dict[str, Any]]:
        """Retorna histórico de registros."""
        return self.registration_history.copy()

    def clear_registration_history(self):
        """Limpa histórico de registros."""
        self.registration_history.clear()
        self.view.show_info("Histórico de registros limpo")

    def search_vehicles(self, search_term: str, search_field: str = "plate") -> List[Dict[str, Any]]:
        """Busca veículos por termo."""
        try:
            results = []
            for record in self.registration_history:
                field_value = str(record.get(search_field, '')).lower()
                if search_term.lower() in field_value:
                    results.append(record)
            return results
        except Exception as e:
            self.view.show_error(f"Erro na busca: {e}")
            return []

    def get_vehicle_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos veículos registrados."""
        try:
            stats = {
                'total_registered': len(self.registration_history),
                'types_count': {},
                'recent_registrations': 0,
                'by_brand': {}
            }
            
            # Contagem por tipo e marca
            for record in self.registration_history:
                vehicle_type = record.get('vehicle_type', 'Outros')
                brand = record.get('brand', 'Não informada')
                
                stats['types_count'][vehicle_type] = stats['types_count'].get(vehicle_type, 0) + 1
                stats['by_brand'][brand] = stats['by_brand'].get(brand, 0) + 1
            
            # Registros recentes (últimas 24h)
            recent_threshold = datetime.now().timestamp() - 24 * 60 * 60
            stats['recent_registrations'] = len([
                r for r in self.registration_history 
                if r['registered_at'].timestamp() > recent_threshold
            ])
            
            return stats
            
        except Exception as e:
            print(f"Erro ao calcular estatísticas: {e}")
            return {}

    def format_plate(self, plate: str) -> str:
        """Formata placa para exibição (Mercosul ou modelo antigo)."""
        cleaned_plate = re.sub(r'[^a-zA-Z0-9]', '', plate).upper()
        
        if re.match(r'^[A-Z]{3}\d{1}[A-Z]{1}\d{2}$', cleaned_plate):
            # Formato Mercosul: AAA1A11
            return f"{cleaned_plate[:3]}-{cleaned_plate[3:]}"
        elif re.match(r'^[A-Z]{3}\d{4}$', cleaned_plate):
            # Formato antigo: AAA1111
            return f"{cleaned_plate[:3]}-{cleaned_plate[3:]}"
        else:
            return plate


# ====================================================================
# CLASSE PARA TESTES E DESENVOLVIMENTO
# ====================================================================

class MockVehicleView:
    """View mock para testes do VehicleRegistrationPresenter."""
    
    def __init__(self):
        self.messages = []
        self.loading_state = False
        self.form_cleared = False
        self.form_data_preserved = False
    
    def show_success(self, message):
        self.messages.append(('success', message))
        print(f"✅ {message}")
    
    def show_error(self, message):
        self.messages.append(('error', message))
        print(f"❌ {message}")
    
    def show_info(self, message):
        self.messages.append(('info', message))
        print(f"ℹ️ {message}")
    
    def show_warning(self, message):
        self.messages.append(('warning', message))
        print(f"⚠️ {message}")
    
    def set_loading(self, loading):
        self.loading_state = loading
        print(f"Loading: {loading}")
    
    def clear_form(self):
        self.form_cleared = True
        print("Formulário limpo")
    
    def preserve_form_data(self):
        self.form_data_preserved = True
        print("Dados do formulário preservados")
    
    def refresh_vehicle_list(self):
        print("Lista de veículos atualizada")


# Exemplo de uso para testes
if __name__ == "__main__":
    view = MockVehicleView()
    presenter = VehicleRegistrationPresenter(view)
    
    # Teste de registro básico
    test_data = {
        "plate": "ABC1D23",
        "model": "ACTROS 2651",
        "vehicle_type": "Caminhão",
        "brand": "MERCEDES-BENZ",
        "color": "BRANCO",
        "manufacture_year": 2023,
        "model_year": 2024,
        "chassis": "9BRDWW39XG4109999",
        "renavam": "12345678901",
        "fuel_type": "Diesel",
        "axle_configuration": "6 Eixos"
    }
    
    # Validação antes do registro
    validation_result = presenter.validate_vehicle_data(test_data)
    print("Validação:", validation_result)
    
    # Registro
    presenter.register_vehicle(test_data)
    
    # Estatísticas
    stats = presenter.get_vehicle_stats()
    print("Estatísticas:", stats)
    
    # Formatação de placa
    formatted_plate = presenter.format_plate("ABC1D23")
    print(f"Placa formatada: {formatted_plate}")