"""
Módulo de Smart Score - Índice de Oportunidade Composto (0-100)
Radar Imobiliário RJ - Algoritmo de scoring para investidores.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List


# ============================================================
# CONFIGURAÇÕES DE PESOS E MAPEAMENTOS
# ============================================================

# Pesos dos componentes (devem somar 1.0)
PESOS_SMART_SCORE = {
    'desconto': 0.35,           # 35% - Desconto percentual
    'liquidez_regional': 0.25,  # 25% - Liquidez do bairro/região
    'financiamento': 0.20,      # 20% - Viabilidade de financiamento
    'modalidade': 0.10,         # 10% - Modalidade de venda
    'tipo_imovel': 0.10,        # 10% - Tipo de imóvel
}

# Normalização: desconto máximo considerado para score 1.0
DESCONTO_MAXIMO_NORM = 60.0  # 60% de deságio = score máximo no componente

# Mapeamento de Liquidez Regional (bairros de alto giro no RJ)
# Nota 1.0 = máxima liquidez, valores proporcionais para demais
LIQUIDEZ_BAIRROS_RJ = {
    # Zona Oeste - Alto giro
    'CAMPO GRANDE': 1.0,
    'SANTA CRUZ': 1.0,
    'BANGU': 0.95,
    'REALENGO': 0.9,
    'PADRE MIGUEL': 0.9,
    'SENADOR CAMARA': 0.85,
    'PACIENCIA': 0.8,
    'COSMOS': 0.8,
    'INHOAIBA': 0.75,
    'ITAGUAÍ': 0.7,
    'SEROPEDICA': 0.65,

    # Zona Norte - Alto giro
    'TIJUCA': 1.0,
    'MADUREIRA': 0.95,
    'CASCADURA': 0.9,
    'MEIER': 0.9,
    'ENGANAO DE DENTRO': 0.85,
    'PIEDADE': 0.85,
    'ABOLICAO': 0.85,
    'ROCHA': 0.8,
    'SAO CRISTOVAO': 0.8,
    'BENFICA': 0.75,
    'VILA ISABEL': 0.85,
    'GRAJAU': 0.8,
    'ANDARAI': 0.8,
    'MARACANA': 0.8,
    'TRIAGEM': 0.75,
    'ROCHA MIRANDA': 0.75,
    'COELHO NETO': 0.7,
    'ACARI': 0.7,
    'VIGARIO GERAL': 0.65,
    'PARADA DE LUCAS': 0.65,
    'VILA DA PENHA': 0.7,
    'PENHA': 0.8,
    'BRAS DE PINA': 0.75,
    'CORDOVIL': 0.7,
    'VISTA ALEGRE': 0.65,
    'TOME': 0.6,
    'ITAQUERA': 0.6,
    'COSTA BARROS': 0.6,
    'PAVUNA': 0.65,

    # Centro e Zona Sul - Alta valorização
    'CENTRO': 0.9,
    'BOTAFOGO': 0.95,
    'COPACABANA': 0.95,
    'IPANEMA': 0.9,
    'LEBLON': 0.85,
    'LEME': 0.9,
    'FLAMENGO': 0.9,
    'CATETE': 0.85,
    'GLORIA': 0.85,
    'LARANJEIRAS': 0.85,
    'COSME VELHO': 0.8,
    'SANTA TERESA': 0.75,
    'URCA': 0.8,
    'SÃO CONRADO': 0.85,
    'BARRA DA TIJUCA': 0.95,
    'RECREIO DOS BANDEIRANTES': 0.9,
    'JACAREPAGUA': 0.85,
    'ITANHANGA': 0.8,
    'CAMORIM': 0.75,
    'VARGEM GRANDE': 0.7,
    'VARGEM PEQUENA': 0.7,
    'GUARATIBA': 0.65,
    'SEPETIBA': 0.7,

    # Niterói e Região Metropolitana
    'NITEROI': 0.95,
    'ICARAI': 0.95,
    'SAO DOMINGOS': 0.85,
    'INGA': 0.85,
    'FONSECA': 0.8,
    'CENTRO NITEROI': 0.9,
    'SAO GONCALO': 0.85,
    'ALCANTARA': 0.8,
    'NEVES': 0.75,
    'MUTUÁ': 0.7,
    'MARACANÃ SG': 0.7,

    # Baixada Fluminense
    'DUQUE DE CAXIAS': 0.85,
    'NOVA IGUACU': 0.85,
    'BELFORD ROXO': 0.8,
    'SAO JOAO DE MERITI': 0.8,
    'NILÓPOLIS': 0.8,
    'MESQUITA': 0.75,
    'QUEIMADOS': 0.7,
    'JAPERI': 0.65,
    'MAGÉ': 0.7,
    'GUAPIMIRIM': 0.65,
    'ITABORAI': 0.7,

    # Região Serrana
    'PETROPOLIS': 0.8,
    'TERESOPOLIS': 0.75,
    'NOVA FRIBURGO': 0.7,
    'MIGUEL PEREIRA': 0.6,
    'PATY DO ALFERES': 0.55,

    # Norte Fluminense
    'CAMPOS DOS GOYTACAZES': 0.8,
    'MACAE': 0.85,
    'CABO FRIO': 0.85,
    'SAO PEDRO DA ALDEIA': 0.75,
    'ARRAIAL DO CABO': 0.7,
    'BUZIOS': 0.75,
    'RIO DAS OSTRAS': 0.75,
    'QUISSAMA': 0.6,
    'CARAPEBUS': 0.55,

    # Sul Fluminense
    'VOLTA REDONDA': 0.85,
    'BARRA MANSA': 0.8,
    'RESENDE': 0.75,
    'PINHEIRAL': 0.7,
    'BARRA DO PIRAI': 0.65,
    'VASSOURAS': 0.6,
    'VALERIA': 0.55,
}

# Valor default para bairros não mapeados
LIQUIDEZ_DEFAULT = 0.5

# Mapeamento Modalidade de Venda
MODALIDADE_SCORE = {
    'Venda Direta Online': 1.0,
    'Venda Online': 1.0,
    'Leilão SFI - Edital Único': 0.7,
    'Leilão SFI': 0.7,
    'Licitação Aberta': 0.5,
    'Outra': 0.3,
}

# Mapeamento Tipo de Imóvel
TIPO_IMOVEL_SCORE = {
    'Apartamento': 1.0,
    'Casa': 0.8,
    'Terreno/Lote': 0.5,
    'Sala Comercial': 0.6,
    'Não identificado': 0.3,
}

# Financiamento
FINANCIAMENTO_SCORE = {
    True: 1.0,
    False: 0.2,
}


def normalizar_bairro_para_liquidez(bairro: str) -> float:
    """
    Retorna score de liquidez (0-1) para um bairro.
    Busca exata normalizada (upper, sem acentos).
    """
    if not bairro or pd.isna(bairro):
        return LIQUIDEZ_DEFAULT

    import unicodedata
    # Normaliza: remove acentos, upper, strip
    bairro_norm = unicodedata.normalize('NFKD', str(bairro)).encode('ASCII', 'ignore').decode('ASCII')
    bairro_norm = bairro_norm.upper().strip()

    return LIQUIDEZ_BAIRROS_RJ.get(bairro_norm, LIQUIDEZ_DEFAULT)


def calcular_componente_desconto(desconto: float) -> float:
    """
    Componente 1: Desconto (peso 35%)
    Normalizado até 60% de deságio. Acima de 60% = 1.0
    """
    if pd.isna(desconto) or desconto < 0:
        return 0.0
    return min(1.0, desconto / DESCONTO_MAXIMO_NORM)


def calcular_componente_liquidez(bairro: str) -> float:
    """
    Componente 2: Liquidez Regional (peso 25%)
    Baseado no mapeamento de bairros de alto giro.
    """
    return normalizar_bairro_para_liquidez(bairro)


def calcular_componente_financiamento(financiavel: bool) -> float:
    """
    Componente 3: Viabilidade de Financiamento (peso 20%)
    Financiável = 1.0, Não financiável = 0.2
    """
    return FINANCIAMENTO_SCORE.get(financiavel, 0.2)


def calcular_componente_modalidade(modalidade: str) -> float:
    """
    Componente 4: Modalidade de Venda (peso 10%)
    Venda Direta Online = 1.0, Leilão SFI = 0.7, Licitação Aberta = 0.5
    """
    if not modalidade or pd.isna(modalidade):
        return MODALIDADE_SCORE.get('Outra', 0.3)
    return MODALIDADE_SCORE.get(str(modalidade).strip(), 0.3)


def calcular_componente_tipo(tipo: str) -> float:
    """
    Componente 5: Tipo de Imóvel (peso 10%)
    Apartamento = 1.0, Casa = 0.8, Terreno/Lote = 0.5
    """
    if not tipo or pd.isna(tipo):
        return TIPO_IMOVEL_SCORE.get('Não identificado', 0.3)
    return TIPO_IMOVEL_SCORE.get(str(tipo).strip(), 0.3)


def calcular_smart_score(row: pd.Series) -> float:
    """
    Calcula Smart Score (0-100) para uma linha do DataFrame.

    Args:
        row: Series com colunas: desconto_informado, bairro_normalizado,
             financiavel, modalidade_venda, tipo_imovel

    Returns:
        Score entre 0 e 100 (float com 1 casa decimal)
    """
    # Componentes normalizados (0-1)
    c1 = calcular_componente_desconto(row.get('desconto_informado', 0))
    c2 = calcular_componente_liquidez(row.get('bairro_normalizado', ''))
    c3 = calcular_componente_financiamento(row.get('financiavel', False))
    c4 = calcular_componente_modalidade(row.get('modalidade_venda', ''))
    c5 = calcular_componente_tipo(row.get('tipo_imovel', ''))

    # Score ponderado
    score = (
        c1 * PESOS_SMART_SCORE['desconto'] +
        c2 * PESOS_SMART_SCORE['liquidez_regional'] +
        c3 * PESOS_SMART_SCORE['financiamento'] +
        c4 * PESOS_SMART_SCORE['modalidade'] +
        c5 * PESOS_SMART_SCORE['tipo_imovel']
    ) * 100

    return round(score, 1)


def aplicar_smart_score(df: pd.DataFrame, coluna_saida: str = 'smart_score') -> pd.DataFrame:
    """
    Aplica cálculo de Smart Score ao DataFrame.

    Args:
        df: DataFrame com colunas necessárias
        coluna_saida: Nome da coluna onde salvar o score

    Returns:
        DataFrame com coluna smart_score adicionada/atualizada
    """
    df = df.copy()

    # Garante colunas necessárias
    colunas_necessarias = ['desconto_informado', 'bairro_normalizado',
                          'financiavel', 'modalidade_venda', 'tipo_imovel']

    for col in colunas_necessarias:
        if col not in df.columns:
            # Valores default se coluna não existir
            if col == 'desconto_informado':
                df[col] = 0.0
            elif col == 'financiavel':
                df[col] = False
            else:
                df[col] = ''

    # Aplica cálculo vetorizado para performance
    df[coluna_saida] = df.apply(calcular_smart_score, axis=1)

    return df


def classificar_oportunidade(score: float) -> str:
    """
    Classifica oportunidade baseada no Smart Score.

    Returns:
        'Gold' (>=80), 'Silver' (60-79), 'Bronze' (40-59), 'Regular' (<40)
    """
    if score >= 80:
        return 'Gold'
    elif score >= 60:
        return 'Silver'
    elif score >= 40:
        return 'Bronze'
    else:
        return 'Regular'


def adicionar_classificacao_oportunidade(df: pd.DataFrame,
                                         coluna_score: str = 'smart_score',
                                         coluna_saida: str = 'classificacao_oportunidade') -> pd.DataFrame:
    """Adiciona classificação textual baseada no Smart Score."""
    df = df.copy()
    df[coluna_saida] = df[coluna_score].apply(classificar_oportunidade)
    return df


def contar_oportunidades_gold(df: pd.DataFrame,
                              coluna_score: str = 'smart_score',
                              desconto_min: float = 50.0,
                              financiavel: bool = True) -> int:
    """
    Conta imóveis 'Oportunidade Gold':
    - Desconto > 50%
    - Financiável = True
    - Smart Score > 80
    """
    mask = (
        (df[coluna_score] > 80) &
        (df['desconto_informado'] > desconto_min) &
        (df['financiavel'] == financiavel)
    )
    return int(mask.sum())


def obter_estatisticas_score(df: pd.DataFrame, coluna_score: str = 'smart_score') -> Dict[str, Any]:
    """Retorna estatísticas detalhadas do Smart Score."""
    scores = df[coluna_score].dropna()

    return {
        'media': round(scores.mean(), 1),
        'mediana': round(scores.median(), 1),
        'min': round(scores.min(), 1),
        'max': round(scores.max(), 1),
        'desvio_padrao': round(scores.std(), 1),
        'quartis': {
            'q1': round(scores.quantile(0.25), 1),
            'q2': round(scores.quantile(0.50), 1),
            'q3': round(scores.quantile(0.75), 1),
        },
        'distribuicao_classificacao': df.apply(
            lambda r: classificar_oportunidade(r[coluna_score]), axis=1
        ).value_counts().to_dict(),
        'oportunidades_gold': contar_oportunidades_gold(df, coluna_score),
    }


# ============================================================
# INTEGRAÇÃO COM PIPELINE EXISTENTE
# ============================================================

def integrar_smart_score_no_transformer(transformer_instance) -> None:
    """
    Monkey-patch para integrar Smart Score no DataTransformer existente.
    Substitui _calcular_score_oportunidade pelo novo algoritmo.

    Uso:
        from src.etl.smart_score import integrar_smart_score_no_transformer
        integrar_smart_score_no_transformer(pipeline.transformer)
    """
    from src.etl.smart_score import aplicar_smart_score

    def novo_calcular_metricas_derivadas(self, imovel):
        # Chama método original para outras métricas
        imovel = self.calcular_metricas_derivadas_original(imovel)

        # Converte para dict temporário para calcular smart_score
        row = pd.Series(imovel.to_dict())
        imovel.smart_score = calcular_smart_score(row)

        return imovel

    # Guarda método original
    transformer_instance.calcular_metricas_derivadas_original = transformer_instance.calcular_metricas_derivadas
    transformer_instance.calcular_metricas_derivadas = novo_calcular_metricas_derivadas.__get__(transformer_instance)


# Função standalone para uso direto no pipeline
def enriquecer_com_smart_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Função principal para usar no pipeline após transformação.
    Adiciona smart_score e classificacao_oportunidade.
    """
    df = aplicar_smart_score(df)
    df = adicionar_classificacao_oportunidade(df)
    return df