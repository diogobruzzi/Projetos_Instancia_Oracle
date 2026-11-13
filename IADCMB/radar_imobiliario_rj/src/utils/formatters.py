"""
Utilitários de formatação para o Radar Imobiliário RJ.
Centraliza formatação de valores monetários, percentuais e números no padrão brasileiro (pt-BR).
"""
import numpy as np
from typing import Optional, Union


def format_brl(value: Union[float, int, None]) -> str:
    """
    Formata valor numérico como moeda brasileira (BRL).

    Exemplos:
    - 807000 → "R$ 807.000,00"
    - 448432 → "R$ 448.432,00"
    - 81881.5 → "R$ 81.881,50"
    - None/NaN → "—"

    Args:
        value: Valor numérico (float, int) ou None

    Returns:
        String formatada no padrão BRL
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        # Converte para float se for int
        val = float(value)
        # Formata com separador de milhar '.' e decimal ','
        formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return "—"


def format_brl_compact(value: Union[float, int, None]) -> str:
    """
    Formata valor monetário compacto (sem centavos).

    Exemplos:
    - 807000 → "R$ 807.000"
    - 448432 → "R$ 448.433"
    - None/NaN → "—"
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        val = float(value)
        formatted = f"{val:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return "—"


def format_percent(value: Union[float, int, None], decimals: int = 1) -> str:
    """
    Formata valor como percentual no padrão brasileiro.

    Exemplos:
    - 60.39 → "60,39%"
    - 45.5 → "45,5%"
    - None/NaN → "—"
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        val = float(value)
        fmt = f"{{:,.{decimals}f}}".format(val).replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{fmt}%"
    except (ValueError, TypeError):
        return "—"


def format_number(value: Union[float, int, None], decimals: int = 0) -> str:
    """
    Formata número genérico no padrão brasileiro.

    Exemplos:
    - 1234.5 → "1.234,5"
    - 1000000 → "1.000.000"
    - None/NaN → "—"
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        val = float(value)
        fmt = f"{{:,.{decimals}f}}".format(val).replace(',', 'X').replace('.', ',').replace('X', '.')
        return fmt
    except (ValueError, TypeError):
        return "—"


def format_int(value: Union[int, float, None]) -> str:
    """
    Formata inteiro no padrão brasileiro.

    Exemplos:
    - 1000000 → "1.000.000"
    - None/NaN → "—"
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"

    try:
        val = int(value)
        return f"{val:,}".replace(',', '.')
    except (ValueError, TypeError):
        return "—"


# ============================================================
# Configurações para Streamlit column_config
# ============================================================

def get_brl_column_config(label: str = "Valor (R$)") -> dict:
    """
    Retorna configuração de coluna Streamlit para valores monetários BRL.
    Usa NumberColumn com format personalizado via formatação brasileira.
    """
    import streamlit as st
    return st.column_config.NumberColumn(
        label,
        format="R$ %.2f",
        help="Valor em Reais (BRL)"
    )


def get_brl_compact_column_config(label: str = "Valor (R$)") -> dict:
    """Configuração para valores monetários sem centavos."""
    import streamlit as st
    return st.column_config.NumberColumn(
        label,
        format="R$ %.0f",
        help="Valor em Reais (BRL)"
    )


def get_percent_column_config(label: str = "Percentual (%)", decimals: int = 1) -> dict:
    """Configuração para colunas de percentual."""
    import streamlit as st
    fmt = f"%.{decimals}f%%"
    return st.column_config.NumberColumn(label, format=fmt)


def get_number_column_config(label: str = "Valor", decimals: int = 0) -> dict:
    """Configuração para números genéricos."""
    import streamlit as st
    fmt = f"%.{decimals}f" if decimals > 0 else "%d"
    return st.column_config.NumberColumn(label, format=fmt)