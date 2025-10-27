# sentry/ui/presenters/merchandise_registration_presenter.py

import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal, InvalidOperation

# ====================================================================
# Imports com Fallbacks Robustos
# ====================================================================
try:
    from sentry.core.use_cases.register_merchandise import RegisterMerchandiseUseCase
except ImportError:
    # Fallback para desenvolvimento
    class RegisterMerchandiseUseCase:
        def __init__(self, merchandise_repo):
            self.merchandise_repo = merchandise_repo
        
        def execute(self, merchandise_data):
            # Simula registro bem-sucedido
            merchandise_data['id'] = 1
            merchandise_data['created_at'] = datetime.now()
            return merchandise_data

try:
    from sentry.infra.database.repositories.merchandise_repo import MerchandiseRepository
except ImportError:
    class MerchandiseRepository:
        def save(self, merchandise_data):
            # Simula salvamento no banco
            merchandise_data['id'] = 1
            return merchandise_data
        
        def find_by_id(self, merchandise_id):
            return {"id": merchandise_id, "description": "Mercadoria Mock"}
        
        def find_all(self):
            return []

try:
    from sentry.core.entities.merchandise import Merchandise
except ImportError:
    class Merchandise:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


class MerchandiseRegistrationPresenter:
    """
    Presenter para registro de mercadorias.
    Gerencia a comunicação entre a view de registro e os casos de uso.
    """
    
    # Categorias pré-definidas de mercadorias
    CATEGORIES = [
        "Eletrônicos",
        "Roupas e Acessórios",
        "Alimentos e Bebidas",
        "Móveis e Decoração",
        "Automotivo",
        "Ferramentas e Construção",
        "Livros e Papelaria",
        "Esportes e Lazer",
        "Saúde e Beleza",
        "Outros"
    ]
    
    # Unidades de medida suportadas
    MEASUREMENT_UNITS = [
        "UN", "KG", "G", "L", "ML", "M", "CM", "M²", "M³", "CX", "PC", "PCT"
    ]

    def __init__(self, view):
        self.view = view
        self._initialize_dependencies()
        self._setup_validation_rules()
        
        # Estado do presenter
        self.current_merchandise = None
        self.registration_history = []
        self.validation_errors = []

    def _initialize_dependencies(self):
        """Inicializa dependências com tratamento robusto de erros."""
        try:
            self.merchandise_repo = MerchandiseRepository()
            self.register_use_case = RegisterMerchandiseUseCase(self.merchandise_repo)
        except Exception as e:
            self._handle_dependency_error(e)

    def _handle_dependency_error(self, error):
        """Trata erros de inicialização de dependências."""
        error_msg = f"Erro na inicialização: {error}"
        print(f"AVISO: {error_msg}")
        
        # Cria instâncias fallback
        self.merchandise_repo = MerchandiseRepository()
        self.register_use_case = RegisterMerchandiseUseCase(self.merchandise_repo)
        
        self.view.show_warning("Algumas funcionalidades podem estar limitadas (modo de desenvolvimento)")

    def _setup_validation_rules(self):
        """Configura regras de validação para dados de mercadoria."""
        self.validation_rules = {
            'description': {
                'required': True,
                'min_length': 3,
                'max_length': 200,
                'pattern': r'^[a-zA-Z0-9\s\-\.,áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]+$'
            },
            'quantity': {
                'required': True,
                'min_value': 0,
                'max_value': 999999
            },
            'unit': {
                'required': True,
                'allowed_values': self.MEASUREMENT_UNITS
            },
            'value': {
                'required': False,
                'min_value': 0,
                'max_value': 9999999.99
            },
            'weight': {
                'required': False,
                'min_value': 0,
                'max_value': 50000
            },
            'category': {
                'required': True,
                'allowed_values': self.CATEGORIES
            }
        }

    # ====================================================================
    # MÉTODOS PRINCIPAIS DE REGISTRO
    # ====================================================================

    def register_merchandise(self, merchandise_data: Dict[str, Any]):
        """
        Registra uma nova mercadoria no sistema.
        
        Args:
            merchandise_data: Dicionário com dados da mercadoria
                - description: descrição da mercadoria (obrigatório)
                - quantity: quantidade (obrigatório)
                - unit: unidade de medida (obrigatório)
                - value: valor unitário (opcional)
                - weight: peso (opcional)
                - category: categoria (obrigatório)
                - ncm_code: código NCM (opcional)
                - hazardous: material perigoso (opcional)
        """
        try:
            # Limpa erros anteriores
            self.validation_errors.clear()
            
            # Valida dados básicos
            if not self._validate_required_fields(merchandise_data):
                return
            
            # Validações específicas
            if not self._perform_comprehensive_validation(merchandise_data):
                return
            
            # Prepara dados para registro
            processed_data = self._prepare_merchandise_data(merchandise_data)
            
            # Configura estado de loading
            self.view.set_loading(True)
            self.view.show_info("Registrando mercadoria...")
            
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
        required_fields = ['description', 'quantity', 'unit', 'category']
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
            self._validate_description(data.get('description', '')),
            self._validate_quantity(data.get('quantity')),
            self._validate_unit(data.get('unit', '')),
            self._validate_value(data.get('value')),
            self._validate_weight(data.get('weight')),
            self._validate_category(data.get('category', '')),
            self._validate_ncm_code(data.get('ncm_code')),
            self._validate_hazardous_material(data)
        ]
        
        return all(validations)

    def _validate_description(self, description: str) -> bool:
        """Valida descrição da mercadoria."""
        rules = self.validation_rules['description']
        
        if not description:
            self.validation_errors.append("Descrição é obrigatória")
            return False
        
        if len(description) < rules['min_length']:
            self.validation_errors.append(f"Descrição muito curta (mínimo {rules['min_length']} caracteres)")
            return False
        
        if len(description) > rules['max_length']:
            self.validation_errors.append(f"Descrição muito longa (máximo {rules['max_length']} caracteres)")
            return False
        
        if not re.match(rules['pattern'], description):
            self.validation_errors.append("Descrição contém caracteres inválidos")
            return False
        
        return True

    def _validate_quantity(self, quantity) -> bool:
        """Valida quantidade."""
        try:
            if quantity is None:
                self.validation_errors.append("Quantidade é obrigatória")
                return False
            
            qty = Decimal(str(quantity))
            rules = self.validation_rules['quantity']
            
            if qty < rules['min_value']:
                self.validation_errors.append(f"Quantidade não pode ser menor que {rules['min_value']}")
                return False
            
            if qty > rules['max_value']:
                self.validation_errors.append(f"Quantidade não pode ser maior que {rules['max_value']}")
                return False
            
            return True
            
        except (InvalidOperation, TypeError, ValueError):
            self.validation_errors.append("Quantidade deve ser um número válido")
            return False

    def _validate_unit(self, unit: str) -> bool:
        """Valida unidade de medida."""
        if not unit:
            self.validation_errors.append("Unidade de medida é obrigatória")
            return False
        
        if unit not in self.validation_rules['unit']['allowed_values']:
            allowed = ", ".join(self.validation_rules['unit']['allowed_values'])
            self.validation_errors.append(f"Unidade inválida. Use: {allowed}")
            return False
        
        return True

    def _validate_value(self, value) -> bool:
        """Valida valor unitário."""
        if value is None or value == "":
            return True  # Opcional
        
        try:
            val = Decimal(str(value))
            rules = self.validation_rules['value']
            
            if val < rules['min_value']:
                self.validation_errors.append(f"Valor não pode ser menor que {rules['min_value']}")
                return False
            
            if val > rules['max_value']:
                self.validation_errors.append(f"Valor não pode ser maior que {rules['max_value']}")
                return False
            
            return True
            
        except (InvalidOperation, TypeError, ValueError):
            self.validation_errors.append("Valor deve ser um número válido")
            return False

    def _validate_weight(self, weight) -> bool:
        """Valida peso."""
        if weight is None or weight == "":
            return True  # Opcional
        
        try:
            w = Decimal(str(weight))
            rules = self.validation_rules['weight']
            
            if w < rules['min_value']:
                self.validation_errors.append(f"Peso não pode ser menor que {rules['min_value']}")
                return False
            
            if w > rules['max_value']:
                self.validation_errors.append(f"Peso não pode ser maior que {rules['max_value']}")
                return False
            
            return True
            
        except (InvalidOperation, TypeError, ValueError):
            self.validation_errors.append("Peso deve ser um número válido")
            return False

    def _validate_category(self, category: str) -> bool:
        """Valida categoria."""
        if not category:
            self.validation_errors.append("Categoria é obrigatória")
            return False
        
        if category not in self.validation_rules['category']['allowed_values']:
            allowed = ", ".join(self.validation_rules['category']['allowed_values'])
            self.validation_errors.append(f"Categoria inválida. Use: {allowed}")
            return False
        
        return True

    def _validate_ncm_code(self, ncm_code: str) -> bool:
        """Valida código NCM."""
        if not ncm_code:
            return True  # Opcional
        
        # Formato NCM: 8 dígitos
        if not re.match(r'^\d{8}$', str(ncm_code)):
            self.validation_errors.append("Código NCM deve ter 8 dígitos")
            return False
        
        return True

    def _validate_hazardous_material(self, data: Dict[str, Any]) -> bool:
        """Valida dados de material perigoso."""
        hazardous = data.get('hazardous', False)
        
        if hazardous:
            # Validações específicas para materiais perigosos
            if not data.get('hazard_class'):
                self.validation_errors.append("Classe de risco é obrigatória para materiais perigosos")
                return False
            
            if not data.get('emergency_contact'):
                self.validation_errors.append("Contato de emergência é obrigatório para materiais perigosos")
                return False
        
        return True

    def _prepare_merchandise_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara e enriquece os dados da mercadoria."""
        processed_data = data.copy()
        
        # Adiciona metadados
        processed_data['registered_at'] = datetime.now()
        processed_data['status'] = 'active'
        
        # Formata valores numéricos
        if 'quantity' in processed_data:
            processed_data['quantity'] = Decimal(str(processed_data['quantity']))
        
        if 'value' in processed_data and processed_data['value']:
            processed_data['value'] = Decimal(str(processed_data['value']))
        
        if 'weight' in processed_data and processed_data['weight']:
            processed_data['weight'] = Decimal(str(processed_data['weight']))
        
        # Normaliza strings
        if 'description' in processed_data:
            processed_data['description'] = processed_data['description'].strip().upper()
        
        if 'category' in processed_data:
            processed_data['category'] = processed_data['category'].strip()
        
        return processed_data

    def _handle_registration_success(self, result: Dict[str, Any], original_data: Dict[str, Any]):
        """Processa registro bem-sucedido."""
        # Adiciona ao histórico
        registration_record = {
            'id': result.get('id', len(self.registration_history) + 1),
            'description': original_data.get('description'),
            'category': original_data.get('category'),
            'quantity': original_data.get('quantity'),
            'unit': original_data.get('unit'),
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
        
        # Atualiza lista de mercadorias se necessário
        if hasattr(self.view, 'refresh_merchandise_list'):
            self.view.refresh_merchandise_list()

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
✅ Mercadoria registrada com sucesso!

📦 Descrição: {record['description']}
🏷️ Categoria: {record['category']}
📊 Quantidade: {record['quantity']} {record['unit']}
🆔 ID: {record['id']}
⏰ Registrado em: {record['registered_at'].strftime('%d/%m/%Y %H:%M')}
        """.strip()

    # ====================================================================
    # MÉTODOS AVANÇADOS DE REGISTRO
    # ====================================================================

    def batch_register_merchandise(self, merchandise_list: List[Dict[str, Any]]):
        """Registra múltiplas mercadorias em lote."""
        results = {
            'successful': [],
            'failed': []
        }
        
        total = len(merchandise_list)
        
        for index, merchandise_data in enumerate(merchandise_list, 1):
            try:
                self.view.show_info(f"Processando {index} de {total}...")
                
                # Validação individual
                self.validation_errors.clear()
                if not self._perform_comprehensive_validation(merchandise_data):
                    results['failed'].append({
                        'data': merchandise_data,
                        'error': " | ".join(self.validation_errors)
                    })
                    continue
                
                # Registro individual
                processed_data = self._prepare_merchandise_data(merchandise_data)
                result = self.register_use_case.execute(processed_data)
                
                results['successful'].append({
                    'data': merchandise_data,
                    'result': result
                })
                
            except Exception as e:
                results['failed'].append({
                    'data': merchandise_data,
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

    def validate_merchandise_data(self, merchandise_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida dados de mercadoria sem registrar.
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
            is_valid = self._perform_comprehensive_validation(merchandise_data)
            
            validation_result['is_valid'] = is_valid
            validation_result['errors'] = self.validation_errors.copy()
            
            # Adiciona avisos e sugestões
            validation_result['warnings'] = self._generate_warnings(merchandise_data)
            validation_result['suggestions'] = self._generate_suggestions(merchandise_data)
            
        except Exception as e:
            validation_result['errors'].append(f"Erro na validação: {e}")
        
        return validation_result

    def _generate_warnings(self, data: Dict[str, Any]) -> List[str]:
        """Gera avisos sobre os dados da mercadoria."""
        warnings = []
        
        # Verifica valor muito alto/baixo
        if data.get('value'):
            value = Decimal(str(data['value']))
            if value > 10000:
                warnings.append("Valor unitário muito alto - verifique se está correto")
            elif value < 1:
                warnings.append("Valor unitário muito baixo - verifique se está correto")
        
        # Verifica quantidade muito alta
        if data.get('quantity'):
            quantity = Decimal(str(data['quantity']))
            if quantity > 1000:
                warnings.append("Quantidade muito alta - confirme a necessidade")
        
        # Verifica material perigoso sem informações completas
        if data.get('hazardous') and not data.get('safety_data_sheet'):
            warnings.append("Material perigoso sem ficha de segurança - documento recomendado")
        
        return warnings

    def _generate_suggestions(self, data: Dict[str, Any]) -> List[str]:
        """Gera sugestões para melhorar os dados."""
        suggestions = []
        
        description = data.get('description', '')
        
        # Sugere categoria baseada na descrição
        if 'ELETR' in description.upper():
            suggestions.append("Sugerimos a categoria 'Eletrônicos'")
        elif 'ROUP' in description.upper() or 'VEST' in description.upper():
            suggestions.append("Sugerimos a categoria 'Roupas e Acessórios'")
        
        # Sugere unidade de medida
        if not data.get('unit'):
            if 'CAIXA' in description.upper():
                suggestions.append("Sugerimos unidade 'CX' para caixas")
            elif 'LITRO' in description.upper():
                suggestions.append("Sugerimos unidade 'L' para líquidos")
        
        return suggestions

    # ====================================================================
    # MÉTODOS UTILITÁRIOS
    # ====================================================================

    def get_categories(self) -> List[str]:
        """Retorna lista de categorias disponíveis."""
        return self.CATEGORIES.copy()

    def get_measurement_units(self) -> List[str]:
        """Retorna lista de unidades de medida."""
        return self.MEASUREMENT_UNITS.copy()

    def get_registration_history(self) -> List[Dict[str, Any]]:
        """Retorna histórico de registros."""
        return self.registration_history.copy()

    def clear_registration_history(self):
        """Limpa histórico de registros."""
        self.registration_history.clear()
        self.view.show_info("Histórico de registros limpo")

    def search_merchandise(self, search_term: str, search_field: str = "description") -> List[Dict[str, Any]]:
        """Busca mercadorias por termo."""
        try:
            # Simula busca - em implementação real, usaria o repositório
            results = []
            for record in self.registration_history:
                field_value = str(record.get(search_field, '')).lower()
                if search_term.lower() in field_value:
                    results.append(record)
            return results
        except Exception as e:
            self.view.show_error(f"Erro na busca: {e}")
            return []

    def get_merchandise_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das mercadorias registradas."""
        try:
            stats = {
                'total_registered': len(self.registration_history),
                'categories_count': {},
                'recent_registrations': 0,
                'total_quantity': 0
            }
            
            # Contagem por categoria
            for record in self.registration_history:
                category = record.get('category', 'Outros')
                stats['categories_count'][category] = stats['categories_count'].get(category, 0) + 1
                
                # Soma quantidades
                quantity = record.get('quantity', 0)
                if isinstance(quantity, (int, float, Decimal)):
                    stats['total_quantity'] += quantity
            
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


# ====================================================================
# CLASSE PARA TESTES E DESENVOLVIMENTO
# ====================================================================

class MockMerchandiseView:
    """View mock para testes do MerchandiseRegistrationPresenter."""
    
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
    
    def refresh_merchandise_list(self):
        print("Lista de mercadorias atualizada")


# Exemplo de uso para testes
if __name__ == "__main__":
    view = MockMerchandiseView()
    presenter = MerchandiseRegistrationPresenter(view)
    
    # Teste de registro básico
    test_data = {
        "description": "Notebook Dell Inspiron 15",
        "quantity": 5,
        "unit": "UN",
        "value": 2500.00,
        "weight": 2.5,
        "category": "Eletrônicos",
        "ncm_code": "84713000"
    }
    
    # Validação antes do registro
    validation_result = presenter.validate_merchandise_data(test_data)
    print("Validação:", validation_result)
    
    # Registro
    presenter.register_merchandise(test_data)
    
    # Estatísticas
    stats = presenter.get_merchandise_stats()
    print("Estatísticas:", stats)