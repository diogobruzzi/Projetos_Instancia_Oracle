"""
Módulo de transformação - Limpeza, enriquecimento e derivação de features.
"""
import re
import unicodedata
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

from src.models.schemas import (
    ImovelRaw, ImovelProcessado, TipoImovel, ModalidadeVenda,
    COLUNAS_PROCESSADO
)
from src.utils.formatters import format_brl, format_brl_compact, format_percent, format_number, format_int


class DataTransformer:
    """Transformador de dados brutos para processados."""

    def __init__(self, config: dict):
        self.config = config
        self.validation_config = config.get('validation', {})
        self.enrichment_config = config.get('enrichment', {})
        self.snapshot_id: Optional[int] = None

    # ===== Conversores =====
    @staticmethod
    def br_price_to_float(val: str) -> float:
        """Converte preço brasileiro (1.234,56) para float."""
        if not val or val.strip() == '' or val.lower() == 'nan':
            return np.nan
        val = val.replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return np.nan

    @staticmethod
    def br_discount_to_float(val: str) -> float:
        """Converte desconto (60.39 = 60,39%) para float."""
        if not val or val.strip() == '' or val.lower() == 'nan':
            return np.nan
        try:
            return float(val)
        except ValueError:
            return np.nan

    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """Normaliza texto: remove acentos, maiúsculas, espaços extras."""
        if not texto:
            return ''
        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
        # Maiúsculas e strip
        texto = texto.upper().strip()
        # Remove espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto)
        return texto

    @staticmethod
    def normalizar_municipio(cidade: str) -> str:
        """Normaliza nome do município para padrão consistente."""
        return DataTransformer.normalizar_texto(cidade)

    @staticmethod
    def normalizar_bairro(bairro: str) -> str:
        """Normaliza nome do bairro."""
        return DataTransformer.normalizar_texto(bairro)

    # ===== Extração de características da descrição =====
    def extrair_caracteristicas(self, descricao: str) -> Dict[str, Any]:
        """Extrai características do imóvel da descrição textual."""
        chars = {}
        if not descricao:
            return chars

        desc_lower = descricao.lower()

        # Tipo de imóvel
        if 'apartamento' in desc_lower:
            chars['tipo_imovel'] = TipoImovel.APARTAMENTO.value
        elif 'casa' in desc_lower:
            chars['tipo_imovel'] = TipoImovel.CASA.value
        elif 'terreno' in desc_lower or 'lote' in desc_lower:
            chars['tipo_imovel'] = TipoImovel.TERRENO_LOTE.value
        elif 'sala' in desc_lower and 'comercial' in desc_lower:
            chars['tipo_imovel'] = TipoImovel.SALA_COMERCIAL.value
        else:
            chars['tipo_imovel'] = TipoImovel.NAO_IDENTIFICADO.value

        # Área privativa (só se > 0)
        match = re.search(r'(\d+[.,]\d+)\s*de\s*área\s*privativa', desc_lower)
        if match:
            val = float(match.group(1).replace(',', '.'))
            if val > 0:
                chars['area_privativa'] = val

        # Área total (só se > 0)
        match = re.search(r'(\d+[.,]\d+)\s*de\s*área\s*total', desc_lower)
        if match:
            val = float(match.group(1).replace(',', '.'))
            if val > 0:
                chars['area_total'] = val

        # Área do terreno (só se > 0)
        match = re.search(r'(\d+[.,]\d+)\s*de\s*área\s*do\s*terreno', desc_lower)
        if match:
            val = float(match.group(1).replace(',', '.'))
            if val > 0:
                chars['area_terreno'] = val

        # Quartos
        match = re.search(r'(\d+)\s*qto', desc_lower)
        if match:
            chars['quartos'] = int(match.group(1))

        # Banheiros - conta ocorrências de WC
        wc_count = len(re.findall(r'\bWC\b', descricao, flags=re.IGNORECASE))
        if wc_count > 0:
            chars['banheiros'] = wc_count
        else:
            # Tenta lavabo
            match = re.search(r'(\d+)\s*lavabo', desc_lower)
            if match:
                chars['banheiros'] = int(match.group(1))

        # Vagas
        match = re.search(r'(\d+)\s*vaga', desc_lower)
        if match:
            chars['vagas'] = int(match.group(1))

        return chars

    # ===== Cálculos derivados =====
    def calcular_metricas_derivadas(self, imovel: ImovelProcessado) -> ImovelProcessado:
        """Calcula métricas derivadas (preço/m², faixas, score)."""

        # Preço por m²
        if imovel.area_privativa and imovel.area_privativa > 0:
            imovel.preco_m2_privativa = imovel.preco / imovel.area_privativa
        if imovel.area_total and imovel.area_total > 0:
            imovel.preco_m2_total = imovel.preco / imovel.area_total
        if imovel.area_terreno and imovel.area_terreno > 0:
            imovel.preco_m2_terreno = imovel.preco / imovel.area_terreno

        # Faixa de preço
        imovel.faixa_preco = self._classificar_faixa_preco(imovel.preco)

        # Faixa de desconto
        imovel.faixa_desconto = self._classificar_faixa_desconto(imovel.desconto_informado)

        # Score de oportunidade (0-100)
        imovel.score_oportunidade = self._calcular_score_oportunidade(imovel)

        return imovel

    def _classificar_faixa_preco(self, preco: float) -> str:
        """Classifica imóvel em faixa de preço."""
        if preco <= 50000:
            return 'Até 50k'
        elif preco <= 100000:
            return '50-100k'
        elif preco <= 150000:
            return '100-150k'
        elif preco <= 200000:
            return '150-200k'
        elif preco <= 300000:
            return '200-300k'
        elif preco <= 500000:
            return '300-500k'
        elif preco <= 1000000:
            return '500k-1M'
        elif preco <= 5000000:
            return '1M-5M'
        else:
            return '5M+'

    def _classificar_faixa_desconto(self, desconto: float) -> str:
        """Classifica imóvel em faixa de desconto."""
        if desconto < 10:
            return '0-10%'
        elif desconto < 20:
            return '10-20%'
        elif desconto < 30:
            return '20-30%'
        elif desconto < 40:
            return '30-40%'
        elif desconto < 50:
            return '40-50%'
        elif desconto < 60:
            return '50-60%'
        elif desconto < 70:
            return '60-70%'
        elif desconto < 80:
            return '70-80%'
        elif desconto < 90:
            return '80-90%'
        else:
            return '90-100%'

    def _calcular_score_oportunidade(self, imovel: ImovelProcessado) -> float:
        """
        Calcula score de oportunidade (0-100).
        Componentes:
        - Desconto percentual (peso 30%)
        - Diferença absoluta avaliação-preço (peso 20%)
        - Preço relativo à mediana municipal (peso 20%)
        - Financiável (peso 10%)
        - Tipo de imóvel (peso 10%)
        - Qualidade dos dados (peso 10%)
        """
        score = 0.0

        # 1. Desconto percentual (0-30 pts)
        # Desconto 40% = 15pts, 50% = 20pts, 60% = 25pts, 70%+ = 30pts
        if imovel.desconto_informado >= 70:
            score += 30
        elif imovel.desconto_informado >= 60:
            score += 25
        elif imovel.desconto_informado >= 50:
            score += 20
        elif imovel.desconto_informado >= 40:
            score += 15
        elif imovel.desconto_informado >= 30:
            score += 10
        elif imovel.desconto_informado >= 20:
            score += 5
        else:
            score += max(0, imovel.desconto_informado / 2)

        # 2. Diferença absoluta (0-20 pts)
        diff_abs = imovel.avaliacao - imovel.preco
        if diff_abs >= 200000:
            score += 20
        elif diff_abs >= 100000:
            score += 15
        elif diff_abs >= 50000:
            score += 10
        elif diff_abs >= 20000:
            score += 5

        # 3. Preço relativo (simplificado - seria melhor com mediana municipal)
        # 0-20 pts baseado em quartis
        # Nota: em produção, usar mediana por município/bairro/tipo
        score += 10  # placeholder

        # 4. Financiável (0-10 pts)
        if imovel.financiavel:
            score += 10

        # 5. Tipo de imóvel (0-10 pts)
        # Apartamentos e casas têm mais liquidez
        if imovel.tipo_imovel == TipoImovel.APARTAMENTO.value:
            score += 10
        elif imovel.tipo_imovel == TipoImovel.CASA.value:
            score += 8
        elif imovel.tipo_imovel == TipoImovel.TERRENO_LOTE.value:
            score += 5

        # 6. Qualidade dos dados (0-10 pts)
        qualidade = 0
        if imovel.area_privativa:
            qualidade += 3
        if imovel.quartos:
            qualidade += 2
        if imovel.banheiros:
            qualidade += 2
        if imovel.vagas:
            qualidade += 2
        if imovel.descricao and len(imovel.descricao) > 50:
            qualidade += 1
        score += min(10, qualidade)

        return round(min(100, max(0, score)), 1)

    # ===== Pipeline principal =====
    def transform(self, df_raw: pd.DataFrame, snapshot_id: int) -> pd.DataFrame:
        """Executa transformação completa do DataFrame bruto."""
        self.snapshot_id = snapshot_id
        resultados = []

        for _, row in df_raw.iterrows():
            try:
                imovel_proc = self._processar_registro(row)
                if imovel_proc:
                    resultados.append(imovel_proc.to_dict())
            except Exception as e:
                # Log do erro mas continua
                print(f"Erro processando {row.get('N° do imóvel', 'N/A')}: {e}")
                continue

        df_proc = pd.DataFrame(resultados)

        # Garantir ordem das colunas
        cols_existentes = [c for c in COLUNAS_PROCESSADO if c in df_proc.columns]
        df_proc = df_proc[cols_existentes]

        return df_proc

    def _processar_registro(self, row: pd.Series) -> Optional[ImovelProcessado]:
        """Processa um único registro."""
        raw = ImovelRaw.from_dict(row.to_dict())

        # Conversões
        preco = self.br_price_to_float(raw.preco_str)
        avaliacao = self.br_price_to_float(raw.avaliacao_str)
        desconto_informado = self.br_discount_to_float(raw.desconto_str)

        # Validações básicas
        if np.isnan(preco) or np.isnan(avaliacao):
            return None

        # Desconto calculado
        desconto_calculado = ((avaliacao - preco) / avaliacao) * 100 if avaliacao > 0 else 0
        diferenca_desconto = abs(desconto_informado - desconto_calculado)

        # Financiável
        financiavel = raw.financiamento.strip().lower() in ['sim', 's', 'yes', 'y', 'true', '1']

        # Normalização geográfica
        cidade_norm = self.normalizar_municipio(raw.cidade)
        bairro_norm = self.normalizar_bairro(raw.bairro)

        # Extração de características
        chars = self.extrair_caracteristicas(raw.descricao)

        # Cria objeto processado
        imovel = ImovelProcessado(
            numero_imovel=raw.numero_imovel,
            uf=raw.uf,
            cidade=raw.cidade,
            cidade_normalizada=cidade_norm,
            bairro=raw.bairro,
            bairro_normalizado=bairro_norm,
            endereco=raw.endereco,
            preco=preco,
            avaliacao=avaliacao,
            desconto_informado=desconto_informado,
            desconto_calculado=round(desconto_calculado, 2),
            diferenca_desconto=round(diferenca_desconto, 2),
            financiavel=financiavel,
            modalidade_venda=raw.modalidade_venda,
            descricao=raw.descricao,
            link_acesso=raw.link_acesso,
            tipo_imovel=chars.get('tipo_imovel', TipoImovel.NAO_IDENTIFICADO.value),
            area_privativa=chars.get('area_privativa'),
            area_total=chars.get('area_total'),
            area_terreno=chars.get('area_terreno'),
            quartos=chars.get('quartos'),
            banheiros=chars.get('banheiros'),
            vagas=chars.get('vagas'),
            snapshot_id=self.snapshot_id,
        )

        # Métricas derivadas
        imovel = self.calcular_metricas_derivadas(imovel)

        return imovel


def transformar_dados(df_raw: pd.DataFrame, config: dict, snapshot_id: int) -> pd.DataFrame:
    """Função de conveniência para transformação rápida."""
    transformer = DataTransformer(config)
    return transformer.transform(df_raw, snapshot_id)