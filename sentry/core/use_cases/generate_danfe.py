# LOGISICA/sentry/core/use_cases/generate_danfe.py

import os
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import xml.etree.ElementTree as ET

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class DanfeGenerationError(Exception):
    """Exceção base para erros de geração de DANFE."""
    pass


class InvalidNFeError(DanfeGenerationError):
    """Exceção para XML de NFe inválido."""
    pass


class PdfGenerationError(DanfeGenerationError):
    """Exceção para erros na geração do PDF."""
    pass


class NFeNotFoundError(DanfeGenerationError):
    """Exceção quando NFe não é encontrada."""
    pass


@dataclass
class NFeData:
    """Estrutura de dados da NFe."""
    chave_acesso: str
    emitente: Dict[str, str]
    destinatario: Dict[str, str]
    produtos: List[Dict[str, Any]]
    totais: Dict[str, Decimal]
    impostos: Dict[str, Decimal]
    transportadora: Optional[Dict[str, str]] = None
    informacoes_adicionais: Optional[str] = None
    protocolo_autorizacao: Optional[str] = None
    data_emissao: Optional[datetime] = None
    data_autorizacao: Optional[datetime] = None


@dataclass
class DanfeConfig:
    """Configurações para geração do DANFE."""
    output_dir: str = "data/danfes"
    template_path: Optional[str] = None
    logo_path: Optional[str] = None
    ambiente: str = "produção"  # produção ou homologação
    formato: str = "A4"  # A4 ou A5
    incluir_qrcode: bool = True
    incluir_consultar: bool = True


@dataclass
class DanfeResult:
    """Resultado da geração do DANFE."""
    file_path: str
    chave_acesso: str
    file_size: int
    pages: int
    generation_time: datetime
    metadata: Dict[str, Any]


class NFeParser(ABC):
    """Interface para parser de NFe."""
    
    @abstractmethod
    def parse(self, xml_content: str) -> NFeData:
        """Parse do XML da NFe para estrutura de dados."""
        pass
    
    @abstractmethod
    def validate_xml(self, xml_content: str) -> bool:
        """Valida o XML da NFe."""
        pass


class NFeXMLParser(NFeParser):
    """Parser para XML de NFe."""
    
    def __init__(self):
        self.namespace = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
    
    def validate_xml(self, xml_content: str) -> bool:
        """
        Valida estrutura básica do XML da NFe.
        
        Args:
            xml_content: Conteúdo XML da NFe
            
        Returns:
            True se XML é válido
        """
        try:
            root = ET.fromstring(xml_content)
            return root.tag.endswith('NFe')
        except ET.ParseError as e:
            logger.error("Erro no parse do XML: %s", e)
            return False
    
    def parse(self, xml_content: str) -> NFeData:
        """
        Parse do XML da NFe para estrutura de dados.
        
        Args:
            xml_content: Conteúdo XML da NFe
            
        Returns:
            NFeData: Dados estruturados da NFe
            
        Raises:
            InvalidNFeError: Se o XML for inválido
        """
        try:
            if not self.validate_xml(xml_content):
                raise InvalidNFeError("XML da NFe é inválido")
            
            root = ET.fromstring(xml_content)
            
            # Encontra a tag infNFe
            inf_nfe = root.find('.//ns:infNFe', self.namespace)
            if inf_nfe is None:
                inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
            
            if inf_nfe is None:
                raise InvalidNFeError("Estrutura XML da NFe não encontrada")
            
            chave_acesso = inf_nfe.get('Id', '')[3:]  # Remove 'NFe' do início
            
            # Parse dos dados básicos
            emitente = self._parse_emitente(inf_nfe)
            destinatario = self._parse_destinatario(inf_nfe)
            produtos = self._parse_produtos(inf_nfe)
            totais = self._parse_totais(inf_nfe)
            impostos = self._parse_impostos(inf_nfe)
            transportadora = self._parse_transportadora(inf_nfe)
            
            return NFeData(
                chave_acesso=chave_acesso,
                emitente=emitente,
                destinatario=destinatario,
                produtos=produtos,
                totais=totais,
                impostos=impostos,
                transportadora=transportadora,
                informacoes_adicionais=self._parse_inf_adicionais(inf_nfe),
                protocolo_autorizacao=self._parse_protocolo(root),
                data_emissao=self._parse_data_emissao(inf_nfe)
            )
            
        except Exception as e:
            logger.error("Erro no parse da NFe: %s", e)
            raise InvalidNFeError(f"Erro no parse da NFe: {str(e)}")
    
    def _parse_emitente(self, inf_nfe: ET.Element) -> Dict[str, str]:
        """Parse dos dados do emitente."""
        emitente = inf_nfe.find('.//ns:emit', self.namespace)
        if emitente is None:
            return {}
        
        return {
            'cnpj': self._get_text(emitente, 'ns:CNPJ'),
            'nome': self._get_text(emitente, 'ns:xNome'),
            'fantasia': self._get_text(emitente, 'ns:xFant'),
            'ie': self._get_text(emitente, 'ns:IE'),
            'endereco': {
                'logradouro': self._get_text(emitente, 'ns:enderEmit/ns:xLgr'),
                'numero': self._get_text(emitente, 'ns:enderEmit/ns:nro'),
                'bairro': self._get_text(emitente, 'ns:enderEmit/ns:xBairro'),
                'municipio': self._get_text(emitente, 'ns:enderEmit/ns:xMun'),
                'uf': self._get_text(emitente, 'ns:enderEmit/ns:UF'),
                'cep': self._get_text(emitente, 'ns:enderEmit/ns:CEP'),
            }
        }
    
    def _parse_destinatario(self, inf_nfe: ET.Element) -> Dict[str, str]:
        """Parse dos dados do destinatário."""
        dest = inf_nfe.find('.//ns:dest', self.namespace)
        if dest is None:
            return {}
        
        return {
            'cnpj': self._get_text(dest, 'ns:CNPJ') or self._get_text(dest, 'ns:CPF'),
            'nome': self._get_text(dest, 'ns:xNome'),
            'ie': self._get_text(dest, 'ns:IE'),
            'endereco': {
                'logradouro': self._get_text(dest, 'ns:enderDest/ns:xLgr'),
                'numero': self._get_text(dest, 'ns:enderDest/ns:nro'),
                'bairro': self._get_text(dest, 'ns:enderDest/ns:xBairro'),
                'municipio': self._get_text(dest, 'ns:enderDest/ns:xMun'),
                'uf': self._get_text(dest, 'ns:enderDest/ns:UF'),
                'cep': self._get_text(dest, 'ns:enderDest/ns:CEP'),
            }
        }
    
    def _parse_produtos(self, inf_nfe: ET.Element) -> List[Dict[str, Any]]:
        """Parse dos produtos."""
        produtos = []
        for det in inf_nfe.findall('.//ns:det', self.namespace):
            prod = det.find('ns:prod', self.namespace)
            if prod is not None:
                produtos.append({
                    'codigo': self._get_text(prod, 'ns:cProd'),
                    'descricao': self._get_text(prod, 'ns:xProd'),
                    'ncm': self._get_text(prod, 'ns:NCM'),
                    'cfop': self._get_text(prod, 'ns:CFOP'),
                    'unidade': self._get_text(prod, 'ns:uCom'),
                    'quantidade': Decimal(self._get_text(prod, 'ns:qCom', '0')),
                    'valor_unitario': Decimal(self._get_text(prod, 'ns:vUnCom', '0')),
                    'valor_total': Decimal(self._get_text(prod, 'ns:vProd', '0')),
                })
        return produtos
    
    def _parse_totais(self, inf_nfe: ET.Element) -> Dict[str, Decimal]:
        """Parse dos totais."""
        total = inf_nfe.find('.//ns:total/ns:ICMSTot', self.namespace)
        if total is None:
            return {}
        
        return {
            'valor_produtos': Decimal(self._get_text(total, 'ns:vProd', '0')),
            'valor_frete': Decimal(self._get_text(total, 'ns:vFrete', '0')),
            'valor_seguro': Decimal(self._get_text(total, 'ns:vSeg', '0')),
            'valor_desconto': Decimal(self._get_text(total, 'ns:vDesc', '0')),
            'valor_ipi': Decimal(self._get_text(total, 'ns:vIPI', '0')),
            'valor_total': Decimal(self._get_text(total, 'ns:vNF', '0')),
        }
    
    def _parse_impostos(self, inf_nfe: ET.Element) -> Dict[str, Decimal]:
        """Parse dos impostos."""
        # Implementação simplificada - expandir conforme necessidade
        return {}
    
    def _parse_transportadora(self, inf_nfe: ET.Element) -> Optional[Dict[str, str]]:
        """Parse dos dados da transportadora."""
        transp = inf_nfe.find('.//ns:transp', self.namespace)
        if transp is None:
            return None
        
        transporta = transp.find('ns:transporta', self.namespace)
        if transporta is None:
            return None
        
        return {
            'cnpj': self._get_text(transporta, 'ns:CNPJ') or self._get_text(transporta, 'ns:CPF'),
            'nome': self._get_text(transporta, 'ns:xNome'),
            'ie': self._get_text(transporta, 'ns:IE'),
            'endereco': self._get_text(transporta, 'ns:xEnder'),
            'municipio': self._get_text(transporta, 'ns:xMun'),
            'uf': self._get_text(transporta, 'ns:UF'),
        }
    
    def _parse_inf_adicionais(self, inf_nfe: ET.Element) -> Optional[str]:
        """Parse das informações adicionais."""
        inf_adic = inf_nfe.find('.//ns:infAdic', self.namespace)
        if inf_adic is not None:
            return self._get_text(inf_adic, 'ns:infCpl')
        return None
    
    def _parse_protocolo(self, root: ET.Element) -> Optional[str]:
        """Parse do protocolo de autorização."""
        prot = root.find('.//ns:protNFe', self.namespace)
        if prot is not None:
            inf_prot = prot.find('ns:infProt', self.namespace)
            if inf_prot is not None:
                return self._get_text(inf_prot, 'ns:nProt')
        return None
    
    def _parse_data_emissao(self, inf_nfe: ET.Element) -> Optional[datetime]:
        """Parse da data de emissão."""
        ide = inf_nfe.find('.//ns:ide', self.namespace)
        if ide is not None:
            dh_emi = self._get_text(ide, 'ns:dhEmi')
            if dh_emi:
                try:
                    return datetime.strptime(dh_emi, '%Y-%m-%dT%H:%M:%S%z')
                except ValueError:
                    return None
        return None
    
    def _get_text(self, element: ET.Element, path: str, default: str = '') -> str:
        """Extrai texto de elemento com namespace."""
        elem = element.find(path, self.namespace)
        return elem.text if elem is not None else default


class DanfeGenerator(ABC):
    """Interface para geradores de DANFE."""
    
    @abstractmethod
    def generate(self, nfe_data: NFeData, output_path: str) -> int:
        """Gera DANFE no formato específico."""
        pass
    
    @abstractmethod
    def get_page_count(self, nfe_data: NFeData) -> int:
        """Calcula número de páginas necessárias."""
        pass


class PdfDanfeGenerator(DanfeGenerator):
    """Gerador de DANFE em PDF."""
    
    def __init__(self, config: DanfeConfig):
        self.config = config
        self._ensure_dependencies()
    
    def _ensure_dependencies(self):
        """Verifica dependências para geração de PDF."""
        try:
            import reportlab
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4, A5
            from reportlab.lib.units import mm
        except ImportError as e:
            raise PdfGenerationError(f"Dependências para PDF não encontradas: {e}")
    
    def get_page_count(self, nfe_data: NFeData) -> int:
        """Calcula número de páginas baseado na quantidade de produtos."""
        produtos_por_pagina = 20 if self.config.formato == "A4" else 10
        return max(1, (len(nfe_data.produtos) + produtos_por_pagina - 1) // produtos_por_pagina)
    
    def generate(self, nfe_data: NFeData, output_path: str) -> int:
        """
        Gera DANFE em PDF.
        
        Args:
            nfe_data: Dados da NFe
            output_path: Caminho de saída
            
        Returns:
            Número de páginas geradas
            
        Raises:
            PdfGenerationError: Em caso de erro na geração
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4, A5
            from reportlab.lib.units import mm
            
            pagesize = A4 if self.config.formato == "A4" else A5
            page_count = self.get_page_count(nfe_data)
            
            c = canvas.Canvas(output_path, pagesize=pagesize)
            
            for page_num in range(page_count):
                self._draw_page(c, nfe_data, page_num, page_count, pagesize)
                if page_num < page_count - 1:
                    c.showPage()
            
            c.save()
            logger.info("DANFE gerado com sucesso: %s (%d páginas)", output_path, page_count)
            return page_count
            
        except Exception as e:
            logger.error("Erro na geração do PDF: %s", e)
            raise PdfGenerationError(f"Erro na geração do PDF: {str(e)}")
    
    def _draw_page(self, canvas, nfe_data: NFeData, page_num: int, total_pages: int, pagesize: Tuple[float, float]):
        """Desenha uma página do DANFE."""
        # Implementação simplificada - expandir com layout completo do DANFE
        width, height = pagesize
        
        # Cabeçalho
        self._draw_header(canvas, nfe_data, width, height)
        
        # Dados do emitente/destinatário
        self._draw_parties(canvas, nfe_data, width, height)
        
        # Produtos (apenas os da página atual)
        produtos_pagina = self._get_produtos_pagina(nfe_data.produtos, page_num)
        self._draw_produtos(canvas, produtos_pagina, width, height)
        
        # Totais
        self._draw_totais(canvas, nfe_data.totais, width, height)
        
        # Rodapé
        self._draw_footer(canvas, nfe_data, page_num, total_pages, width, height)
    
    def _draw_header(self, canvas, nfe_data: NFeData, width: float, height: float):
        """Desenha cabeçalho do DANFE."""
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(20 * mm, height - 20 * mm, "DANFE")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(20 * mm, height - 25 * mm, f"Chave de Acesso: {nfe_data.chave_acesso}")
    
    def _draw_parties(self, canvas, nfe_data: NFeData, width: float, height: float):
        """Desenha dados do emitente e destinatário."""
        # Implementar desenho dos dados das partes
        pass
    
    def _draw_produtos(self, canvas, produtos: List[Dict], width: float, height: float):
        """Desenha tabela de produtos."""
        # Implementar tabela de produtos
        pass
    
    def _draw_totais(self, canvas, totais: Dict[str, Decimal], width: float, height: float):
        """Desenha totais da NFe."""
        # Implementar seção de totais
        pass
    
    def _draw_footer(self, canvas, nfe_data: NFeData, page_num: int, total_pages: int, width: float, height: float):
        """Desenha rodapé do DANFE."""
        canvas.setFont("Helvetica", 6)
        canvas.drawString(20 * mm, 10 * mm, f"Página {page_num + 1} de {total_pages}")
    
    def _get_produtos_pagina(self, produtos: List[Dict], page_num: int) -> List[Dict]:
        """Retorna produtos da página específica."""
        produtos_por_pagina = 20 if self.config.formato == "A4" else 10
        start_idx = page_num * produtos_por_pagina
        end_idx = start_idx + produtos_por_pagina
        return produtos[start_idx:end_idx]


class DanfeDirectoryManager:
    """Gerenciador de diretórios para DANFEs."""
    
    def __init__(self, base_dir: str = "data/danfes"):
        self.base_dir = Path(base_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Garante que os diretórios existam."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise DanfeGenerationError(f"Erro ao criar diretório: {e}")
    
    def generate_file_path(self, chave_acesso: str) -> str:
        """Gera caminho único para arquivo DANFE."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DANFE_{chave_acesso}_{timestamp}.pdf"
        return str(self.base_dir / filename)
    
    def get_file_size(self, file_path: str) -> int:
        """Obtém tamanho do arquivo em bytes."""
        try:
            return Path(file_path).stat().st_size
        except Exception as e:
            logger.warning("Erro ao obter tamanho do arquivo: %s", e)
            return 0


class GenerateDanfeUseCase:
    """
    Caso de uso para geração de DANFE.
    
    Responsável por orquestrar todo o processo:
    - Validação do XML
    - Parse dos dados
    - Geração do PDF
    - Retorno de metadados
    """
    
    def __init__(
        self,
        nfe_parser: NFeParser,
        danfe_generator: DanfeGenerator,
        directory_manager: Optional[DanfeDirectoryManager] = None,
        config: Optional[DanfeConfig] = None
    ):
        self.nfe_parser = nfe_parser
        self.danfe_generator = danfe_generator
        self.directory_manager = directory_manager or DanfeDirectoryManager()
        self.config = config or DanfeConfig()
    
    def execute(self, nfe_xml: str) -> DanfeResult:
        """
        Executa a geração do DANFE.
        
        Args:
            nfe_xml: XML da NFe como string
            
        Returns:
            DanfeResult: Resultado com metadados
            
        Raises:
            DanfeGenerationError: Em caso de erro na geração
        """
        logger.info("Iniciando geração de DANFE")
        start_time = datetime.now()
        
        try:
            # 1. Parse do XML
            nfe_data = self.nfe_parser.parse(nfe_xml)
            logger.info("NFe parseada: %s", nfe_data.chave_acesso)
            
            # 2. Gerar caminho do arquivo
            output_path = self.directory_manager.generate_file_path(nfe_data.chave_acesso)
            
            # 3. Gerar PDF
            pages = self.danfe_generator.generate(nfe_data, output_path)
            
            # 4. Coletar metadados
            file_size = self.directory_manager.get_file_size(output_path)
            generation_time = datetime.now() - start_time
            
            result = DanfeResult(
                file_path=output_path,
                chave_acesso=nfe_data.chave_acesso,
                file_size=file_size,
                pages=pages,
                generation_time=datetime.now(),
                metadata={
                    'emitente_cnpj': nfe_data.emitente.get('cnpj'),
                    'destinatario_cnpj': nfe_data.destinatario.get('cnpj'),
                    'valor_total': float(nfe_data.totais.get('valor_total', 0)),
                    'quantidade_produtos': len(nfe_data.produtos),
                    'generation_time_seconds': generation_time.total_seconds(),
                    'formato': self.config.formato,
                }
            )
            
            logger.info(
                "DANFE gerado com sucesso: %s (%d páginas, %d bytes)",
                output_path, pages, file_size
            )
            
            return result
            
        except (InvalidNFeError, PdfGenerationError):
            # Re-lança exceções específicas
            raise
        except Exception as e:
            logger.error("Erro inesperado na geração do DANFE: %s", e)
            raise DanfeGenerationError(f"Erro na geração do DANFE: {str(e)}")
    
    def execute_from_file(self, xml_file_path: str) -> DanfeResult:
        """
        Executa geração do DANFE a partir de arquivo XML.
        
        Args:
            xml_file_path: Caminho do arquivo XML
            
        Returns:
            DanfeResult: Resultado com metadados
        """
        try:
            with open(xml_file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            return self.execute(xml_content)
        except FileNotFoundError:
            raise NFeNotFoundError(f"Arquivo XML não encontrado: {xml_file_path}")
        except Exception as e:
            raise DanfeGenerationError(f"Erro ao ler arquivo XML: {str(e)}")


# Fábrica para criação do use case
class DanfeUseCaseFactory:
    """Fábrica para criar instância do use case com dependências."""
    
    @staticmethod
    def create(config: Optional[DanfeConfig] = None) -> GenerateDanfeUseCase:
        """Cria instância configurada do use case."""
        config = config or DanfeConfig()
        parser = NFeXMLParser()
        generator = PdfDanfeGenerator(config)
        directory_manager = DanfeDirectoryManager(config.output_dir)
        
        return GenerateDanfeUseCase(
            nfe_parser=parser,
            danfe_generator=generator,
            directory_manager=directory_manager,
            config=config
        )


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Exemplo de uso
        config = DanfeConfig(
            output_dir="data/danfes",
            formato="A4",
            ambiente="produção"
        )
        
        use_case = DanfeUseCaseFactory.create(config)
        
        # Exemplo com XML direto
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
            <!-- Conteúdo completo da NFe -->
        </nfeProc>"""
        
        result = use_case.execute(xml_content)
        print(f"DANFE gerado: {result.file_path}")
        print(f"Chave: {result.chave_acesso}")
        print(f"Páginas: {result.pages}")
        print(f"Tamanho: {result.file_size} bytes")
        
    except DanfeGenerationError as e:
        print(f"Erro na geração do DANFE: {e}")