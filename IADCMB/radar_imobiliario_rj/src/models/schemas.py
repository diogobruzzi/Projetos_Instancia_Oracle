"""
Modelos de dados e schemas de validação para o Radar Imobiliário RJ.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd


class TipoImovel(str, Enum):
    APARTAMENTO = "Apartamento"
    CASA = "Casa"
    TERRENO_LOTE = "Terreno/Lote"
    SALA_COMERCIAL = "Sala Comercial"
    NAO_IDENTIFICADO = "Não identificado"


class ModalidadeVenda(str, Enum):
    VENDA_DIRETA_ONLINE = "Venda Direta Online"
    VENDA_ONLINE = "Venda Online"
    LEILAO_SFI = "Leilão SFI - Edital Único"
    LICITACAO_ABERTA = "Licitação Aberta"
    OUTRA = "Outra"


class StatusHistorico(str, Enum):
    NOVO = "Novo"
    ATIVO = "Ativo"
    AUSENTE = "Ausente"
    REAPARECEU = "Reapareceu"


@dataclass
class ImovelRaw:
    """Schema do CSV original (dados brutos)."""
    numero_imovel: str
    uf: str
    cidade: str
    bairro: str
    endereco: str
    preco_str: str
    avaliacao_str: str
    desconto_str: str
    financiamento: str
    descricao: str
    modalidade_venda: str
    link_acesso: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ImovelRaw':
        return cls(
            numero_imovel=data.get('N° do imóvel', '').strip(),
            uf=data.get('UF', '').strip(),
            cidade=data.get('Cidade', '').strip(),
            bairro=data.get('Bairro', '').strip(),
            endereco=data.get('Endereço', '').strip(),
            preco_str=data.get('Preço', '').strip(),
            avaliacao_str=data.get('Valor de avaliação', '').strip(),
            desconto_str=data.get('Desconto', '').strip(),
            financiamento=data.get('Financiamento', '').strip(),
            descricao=data.get('Descrição', '').strip(),
            modalidade_venda=data.get('Modalidade de venda', '').strip(),
            link_acesso=data.get('Link de acesso', '').strip(),
        )


@dataclass
class ImovelProcessado:
    """Schema do imóvel após processamento e enriquecimento."""
    # Identificação
    numero_imovel: str
    uf: str
    cidade: str
    cidade_normalizada: str
    bairro: str
    bairro_normalizado: str
    endereco: str

    # Valores monetários (float)
    preco: float
    avaliacao: float
    desconto_informado: float
    desconto_calculado: float
    diferenca_desconto: float

    # Características
    financiavel: bool
    modalidade_venda: str
    descricao: str
    link_acesso: str

    # Características extraídas
    tipo_imovel: str
    area_privativa: Optional[float] = None
    area_total: Optional[float] = None
    area_terreno: Optional[float] = None
    quartos: Optional[int] = None
    banheiros: Optional[int] = None
    vagas: Optional[int] = None

    # Métricas derivadas
    preco_m2_privativa: Optional[float] = None
    preco_m2_total: Optional[float] = None
    preco_m2_terreno: Optional[float] = None

    # Score e classificação
    score_oportunidade: Optional[float] = None
    faixa_preco: Optional[str] = None
    faixa_desconto: Optional[str] = None

    # Metadados
    data_processamento: datetime = field(default_factory=datetime.now)
    snapshot_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'numero_imovel': self.numero_imovel,
            'uf': self.uf,
            'cidade': self.cidade,
            'cidade_normalizada': self.cidade_normalizada,
            'bairro': self.bairro,
            'bairro_normalizado': self.bairro_normalizado,
            'endereco': self.endereco,
            'preco': self.preco,
            'avaliacao': self.avaliacao,
            'desconto_informado': self.desconto_informado,
            'desconto_calculado': self.desconto_calculado,
            'diferenca_desconto': self.diferenca_desconto,
            'financiavel': self.financiavel,
            'modalidade_venda': self.modalidade_venda,
            'descricao': self.descricao,
            'link_acesso': self.link_acesso,
            'tipo_imovel': self.tipo_imovel,
            'area_privativa': self.area_privativa,
            'area_total': self.area_total,
            'area_terreno': self.area_terreno,
            'quartos': self.quartos,
            'banheiros': self.banheiros,
            'vagas': self.vagas,
            'preco_m2_privativa': self.preco_m2_privativa,
            'preco_m2_total': self.preco_m2_total,
            'preco_m2_terreno': self.preco_m2_terreno,
            'score_oportunidade': self.score_oportunidade,
            'faixa_preco': self.faixa_preco,
            'faixa_desconto': self.faixa_desconto,
            'data_processamento': self.data_processamento.isoformat() if self.data_processamento else None,
            'snapshot_id': self.snapshot_id,
        }


@dataclass
class ValidacaoResultado:
    """Resultado da validação de um registro."""
    numero_imovel: str
    valido: bool
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    def adicionar_erro(self, msg: str):
        self.erros.append(msg)
        self.valido = False

    def adicionar_aviso(self, msg: str):
        self.avisos.append(msg)


@dataclass
class RelatorioQualidade:
    """Relatório de qualidade da importação."""
    total_registros: int = 0
    registros_validos: int = 0
    registros_rejeitados: int = 0
    registros_com_avisos: int = 0
    erros_por_tipo: Dict[str, int] = field(default_factory=dict)
    avisos_por_tipo: Dict[str, int] = field(default_factory=dict)
    detalhes: List[ValidacaoResultado] = field(default_factory=list)

    def adicionar(self, resultado: ValidacaoResultado):
        self.total_registros += 1
        if resultado.valido:
            self.registros_validos += 1
        else:
            self.registros_rejeitados += 1
        if resultado.avisos:
            self.registros_com_avisos += 1
        for erro in resultado.erros:
            self.erros_por_tipo[erro] = self.erros_por_tipo.get(erro, 0) + 1
        for aviso in resultado.avisos:
            self.avisos_por_tipo[aviso] = self.avisos_por_tipo.get(aviso, 0) + 1
        self.detalhes.append(resultado)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.to_dict() for r in self.detalhes])

    def resumo(self) -> str:
        return f"""
=== RELATÓRIO DE QUALIDADE ===
Total de registros: {self.total_registros}
Válidos: {self.registros_validos} ({self.registros_validos/self.total_registros*100:.1f}%)
Rejeitados: {self.registros_rejeitados} ({self.registros_rejeitados/self.total_registros*100:.1f}%)
Com avisos: {self.registros_com_avisos} ({self.registros_com_avisos/self.total_registros*100:.1f}%)

Top 5 Erros:
{self._top_n(self.erros_por_tipo, 5)}

Top 5 Avisos:
{self._top_n(self.avisos_por_tipo, 5)}
        """

    def _top_n(self, d: Dict[str, int], n: int) -> str:
        if not d:
            return "  (nenhum)"
        items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]
        return "\n".join(f"  {k}: {v}" for k, v in items)


# Colunas do DataFrame processado (ordem padrão)
COLUNAS_PROCESSADO = [
    'numero_imovel', 'uf', 'cidade', 'cidade_normalizada', 'bairro', 'bairro_normalizado',
    'endereco', 'preco', 'avaliacao', 'desconto_informado', 'desconto_calculado',
    'diferenca_desconto', 'financiavel', 'modalidade_venda', 'descricao', 'link_acesso',
    'tipo_imovel', 'area_privativa', 'area_total', 'area_terreno',
    'quartos', 'banheiros', 'vagas', 'preco_m2_privativa', 'preco_m2_total', 'preco_m2_terreno',
    'score_oportunidade', 'faixa_preco', 'faixa_desconto',
    'data_processamento', 'snapshot_id'
]