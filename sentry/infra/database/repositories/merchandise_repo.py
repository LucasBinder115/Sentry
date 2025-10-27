# sentry/infra/database/repositories/merchandise_repo.py

import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager

from sentry.core.entities.merchandise import Merchandise
from sentry.core.use_cases.register_merchandise import (
    MerchandiseRegistrationError,
    VehicleNotFoundError
)

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseError(MerchandiseRegistrationError):
    """Exceção para erros de banco de dados."""
    pass


class MerchandiseNotFoundError(MerchandiseRegistrationError):
    """Exceção quando mercadoria não é encontrada."""
    pass


class MerchandiseRepository:
    """
    Repositório para operações de banco de dados com mercadorias.
    
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
                timeout=30.0,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row
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
            
            # Tabela principal de mercadorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchandise (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    weight REAL,
                    volume REAL,
                    vehicle_plate TEXT,
                    notes TEXT,
                    -- Informações adicionais
                    category TEXT DEFAULT 'outros',
                    value REAL,
                    insurance_required BOOLEAN DEFAULT FALSE,
                    fragile BOOLEAN DEFAULT FALSE,
                    hazardous BOOLEAN DEFAULT FALSE,
                    special_handling TEXT,
                    storage_temperature TEXT,
                    -- Metadados
                    status TEXT DEFAULT 'registered',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    registered_by TEXT,
                    -- Chaves estrangeiras
                    carrier_id INTEGER,
                    -- Índices e constraints
                    CONSTRAINT fk_carrier FOREIGN KEY (carrier_id) REFERENCES carriers(id),
                    CONSTRAINT chk_weight CHECK (weight IS NULL OR weight >= 0),
                    CONSTRAINT chk_volume CHECK (volume IS NULL OR volume >= 0),
                    CONSTRAINT chk_value CHECK (value IS NULL OR value >= 0),
                    CONSTRAINT chk_status CHECK (status IN ('registered', 'in_transit', 'delivered', 'cancelled'))
                )
            """)

            # Migrações suaves: garantir colunas obrigatórias em bancos antigos
            try:
                cursor.execute("PRAGMA table_info(merchandise)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                if 'status' not in existing_columns:
                    logger.warning("Coluna ausente: merchandise.status → adicionando...")
                    cursor.execute("ALTER TABLE merchandise ADD COLUMN status TEXT DEFAULT 'registered'")

                if 'created_at' not in existing_columns:
                    logger.warning("Coluna ausente: merchandise.created_at → adicionando...")
                    cursor.execute("ALTER TABLE merchandise ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

                if 'updated_at' not in existing_columns:
                    logger.warning("Coluna ausente: merchandise.updated_at → adicionando...")
                    cursor.execute("ALTER TABLE merchandise ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            except sqlite3.Error as e:
                logger.error("Erro ao aplicar migrações de merchandise: %s", e)
            
            # Tabela para histórico de movimentação de mercadorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchandise_movement (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    merchandise_id INTEGER NOT NULL,
                    from_location TEXT,
                    to_location TEXT,
                    movement_type TEXT NOT NULL,
                    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responsible_person TEXT,
                    notes TEXT,
                    -- Metadados
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_merchandise FOREIGN KEY (merchandise_id) REFERENCES merchandise(id)
                )
            """)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchandise_vehicle ON merchandise(vehicle_plate)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchandise_status ON merchandise(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchandise_category ON merchandise(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchandise_created_at ON merchandise(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchandise_carrier ON merchandise(carrier_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movement_merchandise ON merchandise_movement(merchandise_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movement_date ON merchandise_movement(movement_date)")
            
            conn.commit()
            logger.debug("Tabelas de mercadorias verificadas/criadas com sucesso")
    
    def _row_to_entity(self, row: sqlite3.Row) -> Merchandise:
        """
        Converte uma linha do banco para entidade Merchandise.
        
        Args:
            row: Linha do banco de dados
            
        Returns:
            Instância de Merchandise
        """
        # Campos básicos
        merchandise_data = {
            'id': row['id'],
            'description': row['description']
        }
        
        # Campos numéricos (convertendo para Decimal quando aplicável)
        numeric_fields = ['weight', 'volume', 'value']
        for field in numeric_fields:
            if row[field] is not None:
                try:
                    merchandise_data[field] = Decimal(str(row[field]))
                except:
                    merchandise_data[field] = None
        
        # Campos de texto
        text_fields = ['vehicle_plate', 'notes', 'category', 'special_handling', 'storage_temperature']
        for field in text_fields:
            if row[field] is not None:
                merchandise_data[field] = row[field]
        
        # Campos booleanos
        boolean_fields = ['insurance_required', 'fragile', 'hazardous']
        for field in boolean_fields:
            if row[field] is not None:
                merchandise_data[field] = bool(row[field])
        
        # Campos adicionais
        additional_fields = ['status', 'carrier_id', 'registered_by', 'created_at', 'updated_at']
        for field in additional_fields:
            if row[field] is not None:
                merchandise_data[field] = row[field]
        
        return Merchandise(**merchandise_data)
    
    def save(self, merchandise: Merchandise) -> Merchandise:
        """
        Salva uma mercadoria no banco de dados.
        
        Args:
            merchandise: Instância de Merchandise a ser salva
            
        Returns:
            Merchandise salva com ID atualizado
            
        Raises:
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Salvando mercadoria: %s", merchandise.description[:50])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO merchandise (
                        description, weight, volume, vehicle_plate, notes,
                        category, value, insurance_required, fragile, hazardous,
                        special_handling, storage_temperature, status, carrier_id, registered_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    merchandise.description,
                    float(merchandise.weight) if merchandise.weight else None,
                    float(merchandise.volume) if merchandise.volume else None,
                    getattr(merchandise, 'vehicle_plate', None),
                    getattr(merchandise, 'notes', None),
                    getattr(merchandise, 'category', 'outros'),
                    float(getattr(merchandise, 'value', 0)) if getattr(merchandise, 'value', None) else None,
                    getattr(merchandise, 'insurance_required', False),
                    getattr(merchandise, 'fragile', False),
                    getattr(merchandise, 'hazardous', False),
                    getattr(merchandise, 'special_handling', None),
                    getattr(merchandise, 'storage_temperature', None),
                    getattr(merchandise, 'status', 'registered'),
                    getattr(merchandise, 'carrier_id', None),
                    getattr(merchandise, 'registered_by', None)
                ))
                
                conn.commit()
                merchandise.id = cursor.lastrowid
                
                # Registra movimento inicial
                self._record_movement(
                    conn, merchandise.id, 'registration',
                    notes='Mercadoria registrada no sistema'
                )
                
                logger.info(
                    "Mercadoria salva com sucesso: %s (ID: %s)",
                    merchandise.description, merchandise.id
                )
                
                return merchandise
                
            except sqlite3.Error as e:
                logger.error("Erro ao salvar mercadoria: %s", e)
                raise DatabaseError(f"Erro ao salvar mercadoria: {str(e)}")
    
    def find_by_id(self, merchandise_id: int) -> Optional[Merchandise]:
        """
        Busca mercadoria por ID.
        
        Args:
            merchandise_id: ID da mercadoria
            
        Returns:
            Instância de Merchandise se encontrada, None caso contrário
        """
        logger.debug("Buscando mercadoria por ID: %s", merchandise_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM merchandise WHERE id = ?", (merchandise_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar mercadoria por ID %s: %s", merchandise_id, e)
                raise DatabaseError(f"Erro ao buscar mercadoria: {str(e)}")
    
    def find_by_vehicle_plate(self, vehicle_plate: str) -> List[Merchandise]:
        """
        Busca mercadorias por placa do veículo.
        
        Args:
            vehicle_plate: Placa do veículo
            
        Returns:
            Lista de mercadorias associadas ao veículo
        """
        logger.debug("Buscando mercadorias por placa: %s", vehicle_plate)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM merchandise 
                    WHERE vehicle_plate = ? AND status != 'cancelled'
                    ORDER BY created_at DESC
                """, (vehicle_plate,))
                
                rows = cursor.fetchall()
                merchandise_list = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontradas %d mercadorias para a placa %s", len(merchandise_list), vehicle_plate)
                return merchandise_list
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar mercadorias por placa %s: %s", vehicle_plate, e)
                raise DatabaseError(f"Erro ao buscar mercadorias: {str(e)}")
    
    def find_all(self, status: Optional[str] = None) -> List[Merchandise]:
        """
        Retorna todas as mercadorias.
        
        Args:
            status: Filtro por status (opcional)
            
        Returns:
            Lista de mercadorias
        """
        logger.debug("Buscando todas as mercadorias (status: %s)", status)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if status:
                    cursor.execute("SELECT * FROM merchandise WHERE status = ? ORDER BY created_at DESC", (status,))
                else:
                    cursor.execute("SELECT * FROM merchandise ORDER BY created_at DESC")
                
                rows = cursor.fetchall()
                merchandise_list = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontradas %d mercadorias", len(merchandise_list))
                return merchandise_list
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar todas as mercadorias: %s", e)
                raise DatabaseError(f"Erro ao buscar mercadorias: {str(e)}")
    
    def update(self, merchandise: Merchandise) -> Merchandise:
        """
        Atualiza uma mercadoria existente.
        
        Args:
            merchandise: Instância de Merchandise com dados atualizados
            
        Returns:
            Merchandise atualizada
            
        Raises:
            MerchandiseNotFoundError: Se a mercadoria não for encontrada
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Atualizando mercadoria ID: %s", merchandise.id)
        
        if not merchandise.id:
            raise MerchandiseNotFoundError("Mercadoria não possui ID para atualização")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE merchandise SET
                        description = ?, weight = ?, volume = ?, vehicle_plate = ?, notes = ?,
                        category = ?, value = ?, insurance_required = ?, fragile = ?, hazardous = ?,
                        special_handling = ?, storage_temperature = ?, status = ?, carrier_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    merchandise.description,
                    float(merchandise.weight) if merchandise.weight else None,
                    float(merchandise.volume) if merchandise.volume else None,
                    getattr(merchandise, 'vehicle_plate', None),
                    getattr(merchandise, 'notes', None),
                    getattr(merchandise, 'category', 'outros'),
                    float(getattr(merchandise, 'value', 0)) if getattr(merchandise, 'value', None) else None,
                    getattr(merchandise, 'insurance_required', False),
                    getattr(merchandise, 'fragile', False),
                    getattr(merchandise, 'hazardous', False),
                    getattr(merchandise, 'special_handling', None),
                    getattr(merchandise, 'storage_temperature', None),
                    getattr(merchandise, 'status', 'registered'),
                    getattr(merchandise, 'carrier_id', None),
                    merchandise.id
                ))
                
                if cursor.rowcount == 0:
                    raise MerchandiseNotFoundError(f"Mercadoria com ID {merchandise.id} não encontrada")
                
                conn.commit()
                logger.info("Mercadoria atualizada com sucesso: ID %s", merchandise.id)
                
                return merchandise
                
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar mercadoria ID %s: %s", merchandise.id, e)
                raise DatabaseError(f"Erro ao atualizar mercadoria: {str(e)}")
    
    def update_status(self, merchandise_id: int, new_status: str, notes: Optional[str] = None) -> bool:
        """
        Atualiza o status de uma mercadoria e registra movimento.
        
        Args:
            merchandise_id: ID da mercadoria
            new_status: Novo status
            notes: Observações sobre a mudança
            
        Returns:
            True se atualizada com sucesso
        """
        logger.info("Atualizando status da mercadoria ID %s para: %s", merchandise_id, new_status)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE merchandise 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (new_status, merchandise_id))
                
                if cursor.rowcount == 0:
                    raise MerchandiseNotFoundError(f"Mercadoria com ID {merchandise_id} não encontrada")
                
                # Registra movimento de mudança de status
                movement_notes = f"Status alterado para: {new_status}"
                if notes:
                    movement_notes += f" - {notes}"
                
                self._record_movement(conn, merchandise_id, 'status_change', notes=movement_notes)
                
                conn.commit()
                logger.info("Status da mercadoria ID %s atualizado para: %s", merchandise_id, new_status)
                return True
                
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar status da mercadoria ID %s: %s", merchandise_id, e)
                raise DatabaseError(f"Erro ao atualizar status: {str(e)}")
    
    def _record_movement(self, conn: sqlite3.Connection, merchandise_id: int, 
                        movement_type: str, from_location: Optional[str] = None,
                        to_location: Optional[str] = None, responsible: Optional[str] = None,
                        notes: Optional[str] = None):
        """
        Registra um movimento de mercadoria no histórico.
        
        Args:
            conn: Conexão com o banco
            merchandise_id: ID da mercadoria
            movement_type: Tipo de movimento
            from_location: Local de origem
            to_location: Local de destino
            responsible: Pessoa responsável
            notes: Observações
        """
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO merchandise_movement (
                    merchandise_id, from_location, to_location, movement_type, responsible_person, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (merchandise_id, from_location, to_location, movement_type, responsible, notes))
        except sqlite3.Error as e:
            logger.warning("Erro ao registrar movimento da mercadoria %s: %s", merchandise_id, e)
    
    def get_movement_history(self, merchandise_id: int) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de movimentação de uma mercadoria.
        
        Args:
            merchandise_id: ID da mercadoria
            
        Returns:
            Lista de movimentos
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM merchandise_movement 
                    WHERE merchandise_id = ? 
                    ORDER BY movement_date DESC
                """, (merchandise_id,))
                
                rows = cursor.fetchall()
                movements = []
                
                for row in rows:
                    movements.append({
                        'id': row['id'],
                        'merchandise_id': row['merchandise_id'],
                        'from_location': row['from_location'],
                        'to_location': row['to_location'],
                        'movement_type': row['movement_type'],
                        'movement_date': row['movement_date'],
                        'responsible_person': row['responsible_person'],
                        'notes': row['notes'],
                        'created_at': row['created_at']
                    })
                
                return movements
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar histórico da mercadoria %s: %s", merchandise_id, e)
                raise DatabaseError(f"Erro ao buscar histórico: {str(e)}")
    
    def search(self, query: str, category: Optional[str] = None) -> List[Merchandise]:
        """
        Busca mercadorias por descrição ou notas.
        
        Args:
            query: Termo de busca
            category: Filtro por categoria (opcional)
            
        Returns:
            Lista de mercadorias encontradas
        """
        logger.debug("Buscando mercadorias com query: '%s', categoria: %s", query, category)
        
        search_term = f"%{query.strip()}%" if query else "%"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if category:
                    cursor.execute("""
                        SELECT * FROM merchandise 
                        WHERE (description LIKE ? OR notes LIKE ?) 
                        AND category = ? AND status != 'cancelled'
                        ORDER BY created_at DESC
                    """, (search_term, search_term, category))
                else:
                    cursor.execute("""
                        SELECT * FROM merchandise 
                        WHERE (description LIKE ? OR notes LIKE ?) 
                        AND status != 'cancelled'
                        ORDER BY created_at DESC
                    """, (search_term, search_term))
                
                rows = cursor.fetchall()
                merchandise_list = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontradas %d mercadorias na busca", len(merchandise_list))
                return merchandise_list
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar mercadorias: %s", e)
                raise DatabaseError(f"Erro na busca de mercadorias: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das mercadorias.
        
        Returns:
            Dicionário com estatísticas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'registered' THEN 1 END) as registered,
                        COUNT(CASE WHEN status = 'in_transit' THEN 1 END) as in_transit,
                        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
                        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled,
                        SUM(weight) as total_weight,
                        SUM(value) as total_value,
                        COUNT(CASE WHEN fragile = 1 THEN 1 END) as fragile_count,
                        COUNT(CASE WHEN hazardous = 1 THEN 1 END) as hazardous_count,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM merchandise
                """)
                
                row = cursor.fetchone()
                
                return {
                    'total': row['total'],
                    'registered': row['registered'],
                    'in_transit': row['in_transit'],
                    'delivered': row['delivered'],
                    'cancelled': row['cancelled'],
                    'total_weight': row['total_weight'],
                    'total_value': row['total_value'],
                    'fragile_count': row['fragile_count'],
                    'hazardous_count': row['hazardous_count'],
                    'oldest_registration': row['oldest'],
                    'newest_registration': row['newest']
                }
                    
            except sqlite3.Error as e:
                logger.error("Erro ao obter estatísticas: %s", e)
                raise DatabaseError(f"Erro ao obter estatísticas: {str(e)}")


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        repo = MerchandiseRepository()
        
        # Teste de criação de mercadoria
        merchandise = Merchandise(
            description="Notebook Dell Inspiron 15 5000",
            weight=Decimal('2.5'),
            volume=Decimal('0.015'),
            vehicle_plate="ABC1D23",
            category="eletronicos",
            value=Decimal('3500.00'),
            fragile=True,
            insurance_required=True,
            notes="Manuseio com cuidado. Produto frágil."
        )
        
        saved_merchandise = repo.save(merchandise)
        print(f"Mercadoria salva: {saved_merchandise.description} (ID: {saved_merchandise.id})")
        
        # Teste de busca
        found_merchandise = repo.find_by_id(saved_merchandise.id)
        if found_merchandise:
            print(f"Mercadoria encontrada: {found_merchandise.description}")
        
        # Estatísticas
        stats = repo.get_stats()
        print(f"Estatísticas: {stats}")
        
    except Exception as e:
        print(f"Erro: {e}")