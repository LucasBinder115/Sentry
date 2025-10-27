# sentry/infra/database/repositories/carrier_repo.py

import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from sentry.core.entities.carrier import Carrier
from sentry.core.use_cases.register_carrier import (
    CarrierRegistrationError,
    DuplicateCNPJError
)

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseError(CarrierRegistrationError):
    """Exceção para erros de banco de dados."""
    pass


class CarrierNotFoundError(CarrierRegistrationError):
    """Exceção quando transportadora não é encontrada."""
    pass


class CarrierRepository:
    """
    Repositório para operações de banco de dados com transportadoras.
    
    Implementa padrão Repository para abstrair o acesso a dados
    e fornecer operações robustas com tratamento de erros.
    """
    
    def __init__(self, db_path: str = "data/database/sentry.db"):
        self.db_path = db_path
        self._ensure_database_dir()
        self._create_tables()
    
    def _ensure_database_dir(self):
        """Garante que o diretório do banco de dados existe."""
        from pathlib import Path
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager para gerenciar conexões com o banco.
        
        Yields:
            sqlite3.Connection: Conexão com o banco de dados
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # Timeout de 30 segundos
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
            yield conn
        except sqlite3.Error as e:
            logger.error("Erro de banco de dados: %s", e)
            raise DatabaseError(f"Erro de banco de dados: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self):
        """Cria as tabelas necessárias se não existirem."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela principal de transportadoras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS carriers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    cnpj TEXT UNIQUE NOT NULL,
                    responsible_name TEXT,
                    contact_phone TEXT,
                    email TEXT,
                    -- Endereço
                    street TEXT,
                    number TEXT,
                    complement TEXT,
                    neighborhood TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    -- Informações adicionais
                    operating_regions TEXT,
                    vehicle_types TEXT,
                    capacity_kg REAL,
                    insurance_value REAL,
                    notes TEXT,
                    -- Metadados
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Índices
                    CONSTRAINT ck_status CHECK (status IN ('active', 'inactive', 'suspended'))
                )
            """)

            # Migrações suaves: garantir colunas obrigatórias em bancos antigos
            try:
                cursor.execute("PRAGMA table_info(carriers)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                if 'status' not in existing_columns:
                    logger.warning("Coluna ausente: carriers.status → adicionando...")
                    cursor.execute("ALTER TABLE carriers ADD COLUMN status TEXT DEFAULT 'active'")

                if 'created_at' not in existing_columns:
                    logger.warning("Coluna ausente: carriers.created_at → adicionando...")
                    cursor.execute("ALTER TABLE carriers ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

                if 'updated_at' not in existing_columns:
                    logger.warning("Coluna ausente: carriers.updated_at → adicionando...")
                    cursor.execute("ALTER TABLE carriers ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            except sqlite3.Error as e:
                logger.error("Erro ao aplicar migrações de carriers: %s", e)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_carriers_cnpj ON carriers(cnpj)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_carriers_status ON carriers(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_carriers_city ON carriers(city)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_carriers_created_at ON carriers(created_at)")
            
            conn.commit()
            
            logger.debug("Tabelas de transportadoras verificadas/criadas com sucesso")
    
    def _row_to_entity(self, row: sqlite3.Row) -> Carrier:
        """
        Converte uma linha do banco para entidade Carrier.
        
        Args:
            row: Linha do banco de dados
            
        Returns:
            Instância de Carrier
        """
        # Campos básicos
        carrier_data = {
            'id': row['id'],
            'name': row['name'],
            'cnpj': row['cnpj']
        }
        
        # Campos opcionais
        optional_fields = [
            'responsible_name', 'contact_phone', 'email',
            'operating_regions', 'vehicle_types', 'capacity_kg',
            'insurance_value', 'notes', 'status'
        ]
        
        for field in optional_fields:
            if row[field] is not None:
                carrier_data[field] = row[field]
        
        # Endereço (se disponível)
        address_fields = ['street', 'number', 'complement', 'neighborhood', 'city', 'state', 'zip_code']
        address_data = {}
        
        for field in address_fields:
            if row[field] is not None:
                address_data[field] = row[field]
        
        if address_data:
            carrier_data['address'] = address_data
        
        # Metadados
        carrier_data['created_at'] = row['created_at']
        carrier_data['updated_at'] = row['updated_at']
        
        return Carrier(**carrier_data)
    
    def save(self, carrier: Carrier) -> Carrier:
        """
        Salva uma transportadora no banco de dados.
        
        Args:
            carrier: Instância de Carrier a ser salva
            
        Returns:
            Carrier salva com ID atualizado
            
        Raises:
            DuplicateCNPJError: Se já existir transportadora com o mesmo CNPJ
            DatabaseError: Em caso de outros erros de banco
        """
        logger.info("Salvando transportadora: %s (CNPJ: %s)", carrier.name, carrier.cnpj)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Prepara dados para inserção
                address = getattr(carrier, 'address', {})
                
                cursor.execute("""
                    INSERT INTO carriers (
                        name, cnpj, responsible_name, contact_phone, email,
                        street, number, complement, neighborhood, city, state, zip_code,
                        operating_regions, vehicle_types, capacity_kg, insurance_value, notes,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    carrier.name,
                    carrier.cnpj,
                    getattr(carrier, 'responsible_name', None),
                    getattr(carrier, 'contact_phone', None),
                    getattr(carrier, 'email', None),
                    address.get('street'),
                    address.get('number'),
                    address.get('complement'),
                    address.get('neighborhood'),
                    address.get('city'),
                    address.get('state'),
                    address.get('zip_code'),
                    getattr(carrier, 'operating_regions', None),
                    getattr(carrier, 'vehicle_types', None),
                    getattr(carrier, 'capacity_kg', None),
                    getattr(carrier, 'insurance_value', None),
                    getattr(carrier, 'notes', None),
                    getattr(carrier, 'status', 'active')
                ))
                
                conn.commit()
                
                # Atualiza ID da entidade
                carrier.id = cursor.lastrowid
                
                logger.info(
                    "Transportadora salva com sucesso: %s (ID: %s)",
                    carrier.name, carrier.id
                )
                
                return carrier
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: carriers.cnpj" in str(e):
                    raise DuplicateCNPJError(
                        f"Já existe uma transportadora cadastrada com o CNPJ: {carrier.cnpj}"
                    )
                else:
                    logger.error("Erro de integridade ao salvar transportadora: %s", e)
                    raise DatabaseError(f"Erro de integridade no banco de dados: {str(e)}")
            
            except sqlite3.Error as e:
                logger.error("Erro ao salvar transportadora: %s", e)
                raise DatabaseError(f"Erro ao salvar transportadora: {str(e)}")
    
    def find_by_cnpj(self, cnpj: str) -> Optional[Carrier]:
        """
        Busca transportadora por CNPJ.
        
        Args:
            cnpj: CNPJ da transportadora
            
        Returns:
            Instância de Carrier se encontrada, None caso contrário
        """
        logger.debug("Buscando transportadora por CNPJ: %s", cnpj)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM carriers WHERE cnpj = ? AND status = 'active'", (cnpj,))
                row = cursor.fetchone()
                
                if row:
                    carrier = self._row_to_entity(row)
                    logger.debug("Transportadora encontrada: %s", carrier.name)
                    return carrier
                else:
                    logger.debug("Nenhuma transportadora encontrada com CNPJ: %s", cnpj)
                    return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar transportadora por CNPJ %s: %s", cnpj, e)
                raise DatabaseError(f"Erro ao buscar transportadora: {str(e)}")
    
    def find_by_id(self, carrier_id: int) -> Optional[Carrier]:
        """
        Busca transportadora por ID.
        
        Args:
            carrier_id: ID da transportadora
            
        Returns:
            Instância de Carrier se encontrada, None caso contrário
        """
        logger.debug("Buscando transportadora por ID: %s", carrier_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM carriers WHERE id = ?", (carrier_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar transportadora por ID %s: %s", carrier_id, e)
                raise DatabaseError(f"Erro ao buscar transportadora: {str(e)}")
    
    def find_all(self, active_only: bool = True) -> List[Carrier]:
        """
        Retorna todas as transportadoras.
        
        Args:
            active_only: Se True, retorna apenas transportadoras ativas
            
        Returns:
            Lista de transportadoras
        """
        logger.debug("Buscando todas as transportadoras (active_only: %s)", active_only)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if active_only:
                    cursor.execute("SELECT * FROM carriers WHERE status = 'active' ORDER BY name")
                else:
                    cursor.execute("SELECT * FROM carriers ORDER BY name")
                
                rows = cursor.fetchall()
                carriers = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontradas %d transportadoras", len(carriers))
                return carriers
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar todas as transportadoras: %s", e)
                raise DatabaseError(f"Erro ao buscar transportadoras: {str(e)}")
    
    def update(self, carrier: Carrier) -> Carrier:
        """
        Atualiza uma transportadora existente.
        
        Args:
            carrier: Instância de Carrier com dados atualizados
            
        Returns:
            Carrier atualizada
            
        Raises:
            CarrierNotFoundError: Se a transportadora não for encontrada
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Atualizando transportadora ID: %s", carrier.id)
        
        if not carrier.id:
            raise CarrierNotFoundError("Transportadora não possui ID para atualização")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                address = getattr(carrier, 'address', {})
                
                cursor.execute("""
                    UPDATE carriers SET
                        name = ?, cnpj = ?, responsible_name = ?, contact_phone = ?, email = ?,
                        street = ?, number = ?, complement = ?, neighborhood = ?, city = ?, state = ?, zip_code = ?,
                        operating_regions = ?, vehicle_types = ?, capacity_kg = ?, insurance_value = ?, notes = ?,
                        status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    carrier.name,
                    carrier.cnpj,
                    getattr(carrier, 'responsible_name', None),
                    getattr(carrier, 'contact_phone', None),
                    getattr(carrier, 'email', None),
                    address.get('street'),
                    address.get('number'),
                    address.get('complement'),
                    address.get('neighborhood'),
                    address.get('city'),
                    address.get('state'),
                    address.get('zip_code'),
                    getattr(carrier, 'operating_regions', None),
                    getattr(carrier, 'vehicle_types', None),
                    getattr(carrier, 'capacity_kg', None),
                    getattr(carrier, 'insurance_value', None),
                    getattr(carrier, 'notes', None),
                    getattr(carrier, 'status', 'active'),
                    carrier.id
                ))
                
                if cursor.rowcount == 0:
                    raise CarrierNotFoundError(f"Transportadora com ID {carrier.id} não encontrada")
                
                conn.commit()
                logger.info("Transportadora atualizada com sucesso: ID %s", carrier.id)
                
                return carrier
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: carriers.cnpj" in str(e):
                    raise DuplicateCNPJError(
                        f"Já existe outra transportadora com o CNPJ: {carrier.cnpj}"
                    )
                else:
                    logger.error("Erro de integridade ao atualizar transportadora: %s", e)
                    raise DatabaseError(f"Erro de integridade no banco de dados: {str(e)}")
            
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar transportadora ID %s: %s", carrier.id, e)
                raise DatabaseError(f"Erro ao atualizar transportadora: {str(e)}")
    
    def delete(self, carrier_id: int) -> bool:
        """
        Exclui uma transportadora (soft delete).
        
        Args:
            carrier_id: ID da transportadora
            
        Returns:
            True se excluída com sucesso
            
        Raises:
            CarrierNotFoundError: Se a transportadora não for encontrada
        """
        logger.info("Excluindo transportadora ID: %s", carrier_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "UPDATE carriers SET status = 'inactive', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (carrier_id,)
                )
                
                if cursor.rowcount == 0:
                    raise CarrierNotFoundError(f"Transportadora com ID {carrier_id} não encontrada")
                
                conn.commit()
                logger.info("Transportadora excluída com sucesso: ID %s", carrier_id)
                return True
                
            except sqlite3.Error as e:
                logger.error("Erro ao excluir transportadora ID %s: %s", carrier_id, e)
                raise DatabaseError(f"Erro ao excluir transportadora: {str(e)}")
    
    def search(self, query: str, active_only: bool = True) -> List[Carrier]:
        """
        Busca transportadoras por nome ou CNPJ.
        
        Args:
            query: Termo de busca
            active_only: Se True, busca apenas transportadoras ativas
            
        Returns:
            Lista de transportadoras encontradas
        """
        logger.debug("Buscando transportadoras com query: '%s'", query)
        
        if not query or not query.strip():
            return self.find_all(active_only)
        
        search_term = f"%{query.strip()}%"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if active_only:
                    cursor.execute("""
                        SELECT * FROM carriers 
                        WHERE (name LIKE ? OR cnpj LIKE ?) AND status = 'active'
                        ORDER BY name
                    """, (search_term, search_term))
                else:
                    cursor.execute("""
                        SELECT * FROM carriers 
                        WHERE name LIKE ? OR cnpj LIKE ?
                        ORDER BY name
                    """, (search_term, search_term))
                
                rows = cursor.fetchall()
                carriers = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontradas %d transportadoras na busca", len(carriers))
                return carriers
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar transportadoras: %s", e)
                raise DatabaseError(f"Erro na busca de transportadoras: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das transportadoras.
        
        Returns:
            Dicionário com estatísticas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                        COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive,
                        COUNT(CASE WHEN status = 'suspended' THEN 1 END) as suspended,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM carriers
                """)
                
                row = cursor.fetchone()
                
                return {
                    'total': row['total'],
                    'active': row['active'],
                    'inactive': row['inactive'],
                    'suspended': row['suspended'],
                    'oldest_registration': row['oldest'],
                    'newest_registration': row['newest']
                }
                    
            except sqlite3.Error as e:
                logger.error("Erro ao obter estatísticas: %s", e)
                raise DatabaseError(f"Erro ao obter estatísticas: {str(e)}")


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        repo = CarrierRepository()
        
        # Teste de criação de transportadora
        carrier = Carrier(
            name="Transportadora Teste LTDA",
            cnpj="12345678000195",
            responsible_name="João Silva",
            contact_phone="(11) 99999-9999",
            email="contato@transportadorateste.com.br"
        )
        
        saved_carrier = repo.save(carrier)
        print(f"Transportadora salva: {saved_carrier.name} (ID: {saved_carrier.id})")
        
        # Teste de busca
        found_carrier = repo.find_by_cnpj("12345678000195")
        if found_carrier:
            print(f"Transportadora encontrada: {found_carrier.name}")
        
        # Estatísticas
        stats = repo.get_stats()
        print(f"Estatísticas: {stats}")
        
    except Exception as e:
        print(f"Erro: {e}")