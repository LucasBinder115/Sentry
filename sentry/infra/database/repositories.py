# sentry/infra/database/repositories/user_repository.py
"""
Repositório de Usuários - Acesso aos dados de usuários
Autor: SENTRY.INC
Versão: 2.0
"""

import sqlite3
import os
from typing import Optional, Dict, List
from datetime import datetime


class UserRepository:
    """Repositório para gerenciamento de usuários no banco de dados"""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o repositório
        
        Args:
            db_path: Caminho para o banco de dados SQLite
        """
        if db_path is None:
            # Caminho padrão relativo ao projeto
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            db_path = os.path.join(project_root, "sentry.db")
        
        self.db_path = db_path
        self.connection = None
        self.connect()
        self.create_table()
    
    def connect(self):
        """Estabelece conexão com o banco de dados"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Permite acesso por nome de coluna
            print(f"✅ Conexão estabelecida com: {self.db_path}")
        except sqlite3.Error as e:
            print(f"❌ Erro ao conectar ao banco: {e}")
            raise
    
    def close(self):
        """Fecha conexão com o banco"""
        if self.connection:
            self.connection.close()
            print("🔌 Conexão fechada")
    
    def create_table(self):
        """Cria a tabela de usuários se não existir"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT,
                    nome_completo TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    nivel_acesso TEXT DEFAULT 'operador',
                    ativo BOOLEAN DEFAULT 1,
                    foto_perfil TEXT,
                    telefone TEXT,
                    departamento TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_count INTEGER DEFAULT 0
                )
            ''')
            
            # Criar índices para melhor performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_username 
                ON users(username)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_email 
                ON users(email)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_nivel_acesso 
                ON users(nivel_acesso)
            ''')
            
            self.connection.commit()
            print("✅ Tabela 'users' verificada/criada")
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao criar tabela: {e}")
            raise
    
    # ========================================================================
    # OPERAÇÕES CRUD
    # ========================================================================
    
    def create(self, user_data: Dict) -> bool:
        """
        Cria novo usuário
        
        Args:
            user_data: Dicionário com dados do usuário
        
        Returns:
            True se sucesso, False caso falhe devido a erro de integridade (ex: username/email duplicado)
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                INSERT INTO users (
                    username, password_hash, salt, nome_completo, email,
                    nivel_acesso, ativo, telefone, departamento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data.get('username'),
                user_data.get('password_hash'),
                user_data.get('salt', ''),
                user_data.get('nome_completo'),
                user_data.get('email'),
                user_data.get('nivel_acesso', 'operador'),
                user_data.get('ativo', True),
                user_data.get('telefone', ''),
                user_data.get('departamento', '')
            ))
            
            # Confirma a transação no banco de dados
            self.connection.commit()
            print(f"✅ Usuário '{user_data.get('username')}' criado com sucesso.")
            return True
            
        except sqlite3.IntegrityError as e:
            # Captura erros como username ou email duplicado
            print(f"❌ Erro de integridade ao criar usuário: {e}")
            return False
            
        except sqlite3.Error as e:
            # Captura outros erros de banco de dados
            print(f"❌ Erro geral do SQLite: {e}")
            return False
        # sentry/infra/database/repositories.py (Ajuste Necessário)

class VehicleRepository:
    # Use a nova função para obter a conexão
    def __init__(self):
        # A nova estrutura de conexão é mais limpa.
        # Você deve importar get_db_connection de database.py
        # self.conn = get_db_connection() 
        # Ou manter a sua original, mas a melhor prática é a importação:
        self.db_path = Config.DB_PATH # Ou DB_PATH do novo database.py

    def save_vehicle(self, plate: str, direction: str, user_id: int = None):
        # Usando with para garantir o fechamento da conexão aqui também
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # data_hora não é mais incluído no INSERT, pois o banco de dados cuida disso.
            cursor.execute(
                "INSERT INTO registros (placa_veiculo, direcao, usuario_id) VALUES (?, ?, ?)",
                (plate, direction, user_id)
            )
            conn.commit() 
            print("✅ Registro de veículo salvo.")