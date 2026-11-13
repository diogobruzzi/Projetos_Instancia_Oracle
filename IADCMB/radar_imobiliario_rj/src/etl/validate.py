"""
Módulo de validação - Regras de qualidade e integridade dos dados.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from src.models.schemas import (
    ImovelProcessado, ValidacaoResultado, RelatorioQualidade,
    TipoImovel
)


class DataValidator:
    """Validador de dados processados."""

    def __init__(self, config: dict):
        self.config = config
        self.validation_config = config.get('validation', {})

        # Thresholds de validação
        self.price_min = self.validation_config.get('price_min', 1000)
        self.price_max = self.validation_config.get('price_max', 50000000)
        self.evaluation_min = self.validation_config.get('evaluation_min', 1000)
        self.evaluation_max = self.validation_config.get('evaluation_max', 50000000)
        self.discount_min = self.validation_config.get('discount_min', 0)
        self.discount_max = self.validation_config.get('discount_max', 100)
        self.max_price_vs_eval_ratio = self.validation_config.get('max_price_vs_evaluation_ratio', 2.0)
        self.max_discount_diff = self.validation_config.get('max_discount_diff_pct', 5.0)

    def validar_registro(self, imovel: ImovelProcessado) -> ValidacaoResultado:
        """Valida um único registro processado."""
        resultado = ValidacaoResultado(
            numero_imovel=imovel.numero_imovel,
            valido=True
        )

        # 1. Identificador
        if not imovel.numero_imovel:
            resultado.adicionar_erro("Número do imóvel ausente")

        # 2. Preço
        if np.isnan(imovel.preco):
            resultado.adicionar_erro("Preço ausente ou inválido")
        elif imovel.preco < self.price_min:
            resultado.adicionar_aviso(f"Preço muito baixo: R$ {imovel.preco:,.2f}")
        elif imovel.preco > self.price_max:
            resultado.adicionar_aviso(f"Preço muito alto: R$ {imovel.preco:,.2f}")

        # 3. Avaliação
        if np.isnan(imovel.avaliacao):
            resultado.adicionar_erro("Avaliação ausente ou inválida")
        elif imovel.avaliacao < self.evaluation_min:
            resultado.adicionar_aviso(f"Avaliação muito baixa: R$ {imovel.avaliacao:,.2f}")
        elif imovel.avaliacao > self.evaluation_max:
            resultado.adicionar_aviso(f"Avaliação muito alta: R$ {imovel.avaliacao:,.2f}")

        # 4. Desconto informado
        if np.isnan(imovel.desconto_informado):
            resultado.adicionar_erro("Desconto informado ausente")
        elif imovel.desconto_informado < self.discount_min:
            resultado.adicionar_erro(f"Desconto negativo: {imovel.desconto_informado:.2f}%")
        elif imovel.desconto_informado > self.discount_max:
            resultado.adicionar_aviso(f"Desconto muito alto: {imovel.desconto_informado:.2f}%")

        # 5. Consistência Preço vs Avaliação
        if not np.isnan(imovel.preco) and not np.isnan(imovel.avaliacao) and imovel.avaliacao > 0:
            ratio = imovel.preco / imovel.avaliacao
            if ratio > self.max_price_vs_eval_ratio:
                resultado.adicionar_aviso(
                    f"Preço {ratio:.1f}x maior que avaliação (R$ {imovel.preco:,.2f} vs R$ {imovel.avaliacao:,.2f})"
                )
            elif imovel.preco > imovel.avaliacao:
                resultado.adicionar_aviso(
                    f"Preço maior que avaliação (desconto negativo implícito)"
                )

        # 6. Consistência Desconto Informado vs Calculado
        if (not np.isnan(imovel.desconto_informado) and
            not np.isnan(imovel.desconto_calculado)):
            diff = abs(imovel.desconto_informado - imovel.desconto_calculado)
            if diff > self.max_discount_diff:
                resultado.adicionar_aviso(
                    f"Desconto inconsistente: informado {imovel.desconto_informado:.2f}% vs calculado {imovel.desconto_calculado:.2f}% (diff: {diff:.2f}%)"
                )

        # 7. Características - avisos de dados faltantes
        if imovel.tipo_imovel == TipoImovel.NAO_IDENTIFICADO.value:
            resultado.adicionar_aviso("Tipo de imóvel não identificado na descrição")

        if imovel.area_privativa is None and imovel.tipo_imovel != TipoImovel.TERRENO_LOTE.value:
            resultado.adicionar_aviso("Área privativa não informada")

        if imovel.quartos is None:
            resultado.adicionar_aviso("Quantidade de quartos não informada")

        if imovel.banheiros is None:
            resultado.adicionar_aviso("Quantidade de banheiros não informada")

        # 8. Link
        if not imovel.link_acesso or not imovel.link_acesso.startswith('http'):
            resultado.adicionar_aviso("Link de acesso inválido ou ausente")

        # 9. UF
        if imovel.uf != 'RJ':
            resultado.adicionar_aviso(f"UF inesperada: {imovel.uf}")

        return resultado

    def validar_dataframe(self, df: pd.DataFrame) -> RelatorioQualidade:
        """Valida todo o DataFrame processado."""
        relatorio = RelatorioQualidade()

        for _, row in df.iterrows():
            imovel = self._row_to_imovel(row)
            resultado = self.validar_registro(imovel)
            relatorio.adicionar(resultado)

        return relatorio

    def _row_to_imovel(self, row: pd.Series) -> ImovelProcessado:
        """Converte linha do DataFrame para ImovelProcessado."""
        return ImovelProcessado(
            numero_imovel=str(row.get('numero_imovel', '')),
            uf=str(row.get('uf', '')),
            cidade=str(row.get('cidade', '')),
            cidade_normalizada=str(row.get('cidade_normalizada', '')),
            bairro=str(row.get('bairro', '')),
            bairro_normalizado=str(row.get('bairro_normalizado', '')),
            endereco=str(row.get('endereco', '')),
            preco=float(row.get('preco', np.nan)),
            avaliacao=float(row.get('avaliacao', np.nan)),
            desconto_informado=float(row.get('desconto_informado', np.nan)),
            desconto_calculado=float(row.get('desconto_calculado', np.nan)),
            diferenca_desconto=float(row.get('diferenca_desconto', np.nan)),
            financiavel=bool(row.get('financiavel', False)),
            modalidade_venda=str(row.get('modalidade_venda', '')),
            descricao=str(row.get('descricao', '')),
            link_acesso=str(row.get('link_acesso', '')),
            tipo_imovel=str(row.get('tipo_imovel', '')),
            area_privativa=float(row['area_privativa']) if pd.notna(row.get('area_privativa')) else None,
            area_total=float(row['area_total']) if pd.notna(row.get('area_total')) else None,
            area_terreno=float(row['area_terreno']) if pd.notna(row.get('area_terreno')) else None,
            quartos=int(row['quartos']) if pd.notna(row.get('quartos')) else None,
            banheiros=int(row['banheiros']) if pd.notna(row.get('banheiros')) else None,
            vagas=int(row['vagas']) if pd.notna(row.get('vagas')) else None,
            preco_m2_privativa=float(row['preco_m2_privativa']) if pd.notna(row.get('preco_m2_privativa')) else None,
            preco_m2_total=float(row['preco_m2_total']) if pd.notna(row.get('preco_m2_total')) else None,
            preco_m2_terreno=float(row['preco_m2_terreno']) if pd.notna(row.get('preco_m2_terreno')) else None,
            score_oportunidade=float(row['score_oportunidade']) if pd.notna(row.get('score_oportunidade')) else None,
            faixa_preco=str(row.get('faixa_preco', '')),
            faixa_desconto=str(row.get('faixa_desconto', '')),
            snapshot_id=int(row['snapshot_id']) if pd.notna(row.get('snapshot_id')) else None,
        )

    def gerar_relatorio_estatistico(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Gera relatório estatístico dos dados validados."""
        return {
            'total_registros': len(df),
            'municipios_unicos': df['cidade_normalizada'].nunique() if 'cidade_normalizada' in df.columns else 0,
            'bairros_unicos': df['bairro_normalizado'].nunique() if 'bairro_normalizado' in df.columns else 0,
            'tipos_imovel': df['tipo_imovel'].value_counts().to_dict() if 'tipo_imovel' in df.columns else {},
            'modalidades': df['modalidade_venda'].value_counts().to_dict() if 'modalidade_venda' in df.columns else {},
            'financiaveis_pct': (df['financiavel'].mean() * 100) if 'financiavel' in df.columns else 0,
            'preco': {
                'media': float(df['preco'].mean()) if 'preco' in df.columns else 0,
                'mediana': float(df['preco'].median()) if 'preco' in df.columns else 0,
                'min': float(df['preco'].min()) if 'preco' in df.columns else 0,
                'max': float(df['preco'].max()) if 'preco' in df.columns else 0,
                'desvio_padrao': float(df['preco'].std()) if 'preco' in df.columns else 0,
            },
            'avaliacao': {
                'media': float(df['avaliacao'].mean()) if 'avaliacao' in df.columns else 0,
                'mediana': float(df['avaliacao'].median()) if 'avaliacao' in df.columns else 0,
            },
            'desconto': {
                'media': float(df['desconto_informado'].mean()) if 'desconto_informado' in df.columns else 0,
                'mediana': float(df['desconto_informado'].median()) if 'desconto_informado' in df.columns else 0,
                'min': float(df['desconto_informado'].min()) if 'desconto_informado' in df.columns else 0,
                'max': float(df['desconto_informado'].max()) if 'desconto_informado' in df.columns else 0,
            },
            'score_oportunidade': {
                'media': float(df['score_oportunidade'].mean()) if 'score_oportunidade' in df.columns else 0,
                'mediana': float(df['score_oportunidade'].median()) if 'score_oportunidade' in df.columns else 0,
            },
            'dados_faltantes': {
                'area_privativa': int(df['area_privativa'].isna().sum()) if 'area_privativa' in df.columns else 0,
                'area_total': int(df['area_total'].isna().sum()) if 'area_total' in df.columns else 0,
                'area_terreno': int(df['area_terreno'].isna().sum()) if 'area_terreno' in df.columns else 0,
                'quartos': int(df['quartos'].isna().sum()) if 'quartos' in df.columns else 0,
                'banheiros': int(df['banheiros'].isna().sum()) if 'banheiros' in df.columns else 0,
                'vagas': int(df['vagas'].isna().sum()) if 'vagas' in df.columns else 0,
            }
        }


def validar_dados(df: pd.DataFrame, config: dict) -> tuple:
    """Função de conveniência para validação rápida."""
    validator = DataValidator(config)
    relatorio = validator.validar_dataframe(df)
    estatisticas = validator.gerar_relatorio_estatistico(df)
    return relatorio, estatisticas