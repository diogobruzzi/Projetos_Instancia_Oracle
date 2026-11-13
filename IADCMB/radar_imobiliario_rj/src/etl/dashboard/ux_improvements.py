"""
Melhorias de UX/UI - Dashboard Radar Imobiliário RJ
Componentes reutilizáveis para filtros sanfona, KPIs Gold e logradouros agrupados.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, Tuple


# ============================================================
# 1. FILTROS EM MENUS SANFONA (ACORDEÃO)
# ============================================================

def render_sidebar_accordion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza sidebar reorganizada em 3 menus sanfona colapsáveis:
    1. 📍 Localização (Município → Bairro → Logradouro)
    2. 🏠 Atributos do Imóvel (Tipo, Quartos, Área, Vagas)
    3. 💰 Condições Comerciais (Preço, Desconto, Score, Financiamento, Modalidade)

    Returns:
        DataFrame filtrado
    """
    st.sidebar.markdown("## 🔍 Filtros Inteligentes")

    # Estado para manter expandidos/colapsados
    if 'filtro_localizacao_expandido' not in st.session_state:
        st.session_state.filtro_localizacao_expandido = True
    if 'filtro_atributos_expandido' not in st.session_state:
        st.session_state.filtro_atributos_expandido = True
    if 'filtro_comerciais_expandido' not in st.session_state:
        st.session_state.filtro_comerciais_expandido = True

    filtered = df.copy()

    # ===== MENU 1: LOCALIZAÇÃO =====
    with st.sidebar.expander("📍 **Localização**", expanded=st.session_state.filtro_localizacao_expandido):
        st.session_state.filtro_localizacao_expandido = True

        # Município
        municipios = ['Todos'] + sorted(df['cidade_normalizada'].dropna().unique().tolist())
        municipio_sel = st.selectbox(
            "Município",
            municipios,
            index=0,
            key="acc_municipio",
            help="Selecione um município para filtrar bairros"
        )

        # Bairro (cascata)
        if municipio_sel != 'Todos':
            df_muni = df[df['cidade_normalizada'] == municipio_sel]
            bairros = ['Todos'] + sorted(df_muni['bairro_normalizado'].dropna().unique().tolist())
        else:
            bairros = ['Todos'] + sorted(df['bairro_normalizado'].dropna().unique().tolist())

        bairro_sel = st.selectbox(
            "Bairro",
            bairros,
            index=0,
            key="acc_bairro",
            help="Filtre por bairro específico"
        )

        # Logradouro (cascata - usa endereco_limpo se disponível)
        coluna_endereco = 'endereco_limpo' if 'endereco_limpo' in df.columns else 'endereco'

        if bairro_sel != 'Todos' and municipio_sel != 'Todos':
            df_bairro = df[(df['cidade_normalizada'] == municipio_sel) & (df['bairro_normalizado'] == bairro_sel)]
        elif bairro_sel != 'Todos':
            df_bairro = df[df['bairro_normalizado'] == bairro_sel]
        else:
            df_bairro = df

        if coluna_endereco in df_bairro.columns:
            logradouros = ['Todos'] + sorted(df_bairro[coluna_endereco].dropna().unique().tolist())
        else:
            logradouros = ['Todos']

        logradouro_sel = st.selectbox(
            "Logradouro/Rua",
            logradouros,
            index=0,
            key="acc_logradouro",
            help="Nome da rua/condomínio (agrupado, sem nº de apto)"
        )

        # Aplica filtros de localização
        if municipio_sel != 'Todos':
            filtered = filtered[filtered['cidade_normalizada'] == municipio_sel]
        if bairro_sel != 'Todos':
            filtered = filtered[filtered['bairro_normalizado'] == bairro_sel]
        if logradouro_sel != 'Todos':
            filtered = filtered[filtered[coluna_endereco] == logradouro_sel]

    # ===== MENU 2: ATRIBUTOS DO IMÓVEL =====
    with st.sidebar.expander("🏠 **Atributos do Imóvel**", expanded=st.session_state.filtro_atributos_expandido):
        st.session_state.filtro_atributos_expandido = True

        # Tipo de Imóvel
        tipos = ['Todos'] + sorted(df['tipo_imovel'].dropna().unique().tolist())
        tipo_sel = st.selectbox(
            "Tipo de Imóvel",
            tipos,
            index=0,
            key="acc_tipo"
        )

        # Quartos
        if 'quartos' in df.columns:
            quartos_opts = ['Todos'] + sorted([int(x) for x in df['quartos'].dropna().unique() if x > 0])
            quartos_sel = st.selectbox("Quartos", quartos_opts, index=0, key="acc_quartos")
        else:
            quartos_sel = 'Todos'

        # Banheiros
        if 'banheiros' in df.columns:
            banhos_opts = ['Todos'] + sorted([int(x) for x in df['banheiros'].dropna().unique() if x > 0])
            banhos_sel = st.selectbox("Banheiros", banhos_opts, index=0, key="acc_banhos")
        else:
            banhos_sel = 'Todos'

        # Vagas
        if 'vagas' in df.columns:
            vagas_opts = ['Todos'] + sorted([int(x) for x in df['vagas'].dropna().unique() if x >= 0])
            vagas_sel = st.selectbox("Vagas", vagas_opts, index=0, key="acc_vagas")
        else:
            vagas_sel = 'Todos'

        # Área Privativa (range)
        if 'area_privativa' in df.columns and df['area_privativa'].notna().any():
            area_min = float(df['area_privativa'].min())
            area_max = float(df['area_privativa'].max())
            area_range = st.slider(
                "Área Privativa (m²)",
                area_min, area_max, (area_min, area_max),
                step=5.0,
                key="acc_area"
            )
        else:
            area_range = None

        # Aplica filtros de atributos
        if tipo_sel != 'Todos':
            filtered = filtered[filtered['tipo_imovel'] == tipo_sel]
        if quartos_sel != 'Todos':
            filtered = filtered[filtered['quartos'] == quartos_sel]
        if banhos_sel != 'Todos':
            filtered = filtered[filtered['banheiros'] == banhos_sel]
        if vagas_sel != 'Todos':
            filtered = filtered[filtered['vagas'] == vagas_sel]
        if area_range:
            filtered = filtered[
                (filtered['area_privativa'] >= area_range[0]) &
                (filtered['area_privativa'] <= area_range[1])
            ]

    # ===== MENU 3: CONDIÇÕES COMERCIAIS =====
    with st.sidebar.expander("💰 **Condições Comerciais**", expanded=st.session_state.filtro_comerciais_expandido):
        st.session_state.filtro_comerciais_expandido = True

        # Modalidade
        modalidades = ['Todas'] + sorted(df['modalidade_venda'].dropna().unique().tolist())
        modalidade_sel = st.selectbox("Modalidade", modalidades, index=0, key="acc_modalidade")

        # Financiamento
        financ_sel = st.selectbox("Financiável", ['Todos', 'Sim', 'Não'], index=0, key="acc_financ")

        # Faixa de Preço (categórica)
        faixas_preco = ['Todas'] + sorted(df['faixa_preco'].dropna().unique().tolist())
        faixa_preco_sel = st.selectbox("Faixa de Preço", faixas_preco, index=0, key="acc_faixa_preco")

        # Faixa de Desconto (categórica)
        faixas_desc = ['Todas'] + sorted(df['faixa_desconto'].dropna().unique().tolist())
        faixa_desc_sel = st.selectbox("Faixa de Desconto", faixas_desc, index=0, key="acc_faixa_desc")

        # Smart Score (range)
        if 'smart_score' in df.columns:
            score_min = st.slider(
                "Smart Score Mínimo",
                0, 100, 0, 5,
                key="acc_score",
                help="Índice de Oportunidade Composto (0-100)"
            )
        else:
            score_min = 0

        # Preço (range numérico)
        preco_min_val = float(df['preco'].min())
        preco_max_val = float(df['preco'].max())
        preco_range = st.slider(
            "Preço (R$)",
            preco_min_val, preco_max_val,
            (preco_min_val, preco_max_val),
            step=10000.0,
            format="R$ %.0f",
            key="acc_preco_range"
        )

        # Aplica filtros comerciais
        if modalidade_sel != 'Todas':
            filtered = filtered[filtered['modalidade_venda'] == modalidade_sel]
        if financ_sel == 'Sim':
            filtered = filtered[filtered['financiavel'] == True]
        elif financ_sel == 'Não':
            filtered = filtered[filtered['financiavel'] == False]
        if faixa_preco_sel != 'Todas':
            filtered = filtered[filtered['faixa_preco'] == faixa_preco_sel]
        if faixa_desc_sel != 'Todas':
            filtered = filtered[filtered['faixa_desconto'] == faixa_desc_sel]
        if score_min > 0:
            filtered = filtered[filtered.get('smart_score', 0) >= score_min]

        filtered = filtered[
            (filtered['preco'] >= preco_range[0]) &
            (filtered['preco'] <= preco_range[1])
        ]

    # Resumo de filtros aplicados
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📊 Registros: {len(filtered):,} / {len(df):,}**")

    if len(filtered) < len(df):
        pct = len(filtered) / len(df) * 100
        st.sidebar.caption(f"Exibindo {pct:.1f}% do total")

    return filtered


# ============================================================
# 2. KPI "OPORTUNIDADES GOLD" - CARD DE DESTAQUE
# ============================================================

def render_kpi_oportunidades_gold(df: pd.DataFrame,
                                   coluna_score: str = 'smart_score',
                                   desconto_min: float = 50.0) -> int:
    """
    Renderiza card KPI destacado para "Oportunidades Gold".

    Critérios:
    - Smart Score > 80
    - Desconto > 50%
    - Financiável = True
    - Ativo = True (se coluna existir)

    Returns:
        Contagem de oportunidades Gold
    """
    # Filtra ativos se coluna existir
    df_ativos = df
    if 'ativo' in df.columns:
        df_ativos = df[df['ativo'] == 1]

    mask_gold = (
        (df_ativos[coluna_score] > 80) &
        (df_ativos['desconto_informado'] > desconto_min) &
        (df_ativos['financiavel'] == True)
    )

    qtd_gold = int(mask_gold.sum())
    pct_gold = (qtd_gold / len(df) * 100) if len(df) > 0 else 0

    # Card estilizado
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3);
        border: 2px solid #FF8C00;
    ">
        <div style="font-size: 0.85rem; color: #8B4513; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
            🏆 Oportunidades Gold
        </div>
        <div style="font-size: 2.5rem; font-weight: 800; color: #1a1a1a; margin: 0.5rem 0;">
            {qtd_gold:,}
        </div>
        <div style="font-size: 0.9rem; color: #8B4513;">
            {pct_gold:.1f}% do catálogo | Score > 80 | Desc > 50% | Financiável
        </div>
    </div>
    """, unsafe_allow_html=True)

    return qtd_gold


def render_kpi_row_completa(df: pd.DataFrame, coluna_score: str = 'smart_score') -> None:
    """Renderiza linha completa de KPIs incluindo Gold."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Imóveis", f"{len(df):,}")

    with col2:
        preco_medio = df['preco'].mean()
        st.metric("Preço Médio", f"R$ {preco_medio:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    with col3:
        desconto_medio = df['desconto_informado'].mean()
        st.metric("Desconto Médio", f"{desconto_medio:.1f}%".replace('.', ','))

    with col4:
        score_medio = df[coluna_score].mean() if coluna_score in df.columns else 0
        st.metric(f"{coluna_score.replace('_', ' ').title()} Médio", f"{score_medio:.1f}".replace('.', ','))

    with col5:
        render_kpi_oportunidades_gold(df, coluna_score)


# ============================================================
# 3. GRÁFICO TOP LOGRADOUROS AGRUPADOS
# ============================================================

def plot_top_logradouros_agrupados(df: pd.DataFrame, top_n: int = 15) -> Optional[go.Figure]:
    """
    Gráfico Top N Logradouros agrupados por endereco_limpo (nome da rua/condomínio).
    Evita duplicação por apartamento/bloco.

    Usa endereco_limpo se disponível, senão endereco original.
    """
    coluna_endereco = 'endereco_limpo' if 'endereco_limpo' in df.columns else 'endereco'

    if coluna_endereco not in df.columns:
        return None

    # Agrupa por logradouro limpo
    rua_stats = df.groupby(coluna_endereco).agg(
        Quantidade=('numero_imovel', 'count'),
        Preco_Medio=('preco', 'mean'),
        Smart_Score_Medio=('smart_score', 'mean') if 'smart_score' in df.columns else ('preco', 'mean'),
        Desconto_Medio=('desconto_informado', 'mean'),
        Financiaveis=('financiavel', 'sum')
    ).sort_values('Quantidade', ascending=False).head(top_n).reset_index()

    rua_stats = rua_stats.sort_values('Quantidade', ascending=True)

    # Formata para hover
    rua_stats['Preco_Medio_Fmt'] = rua_stats['Preco_Medio'].apply(
        lambda x: f"R$ {x:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    rua_stats['Score_Fmt'] = rua_stats['Smart_Score_Medio'].apply(lambda x: f"{x:.1f}".replace('.', ','))

    # Cor pelo Smart Score médio (se disponível) ou preço
    cor_coluna = 'Smart_Score_Medio' if 'smart_score' in df.columns else 'Preco_Medio'
    cor_titulo = "Smart Score Médio" if 'smart_score' in df.columns else "Preço Médio (R$)"

    fig = px.bar(
        rua_stats,
        x='Quantidade',
        y=coluna_endereco,
        orientation='h',
        color=cor_coluna,
        color_continuous_scale='RdYlGn' if 'smart_score' in df.columns else 'Oranges',
        text='Quantidade',
        hover_data={
            'Quantidade': True,
            'Preco_Medio': False,
            'Preco_Medio_Fmt': True,
            'Smart_Score_Medio': False,
            'Score_Fmt': True,
            'Desconto_Medio': ':,.1f',
            'Financiaveis': True
        }
    )

    fig.update_traces(
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Quantidade: %{x}<br>'
            'Preço Médio: %{customdata[0]}<br>'
            'Smart Score: %{customdata[1]}<br>'
            'Desc. Médio: %{customdata[2]:.1f}%<br>'
            'Financiáveis: %{customdata[3]}<extra></extra>'
        )
    )

    fig.update_layout(
        showlegend=False,
        height=max(400, top_n * 28),
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Quantidade de Imóveis",
        yaxis_title=None,
        coloraxis_colorbar=dict(
            title=cor_titulo,
            thickness=15,
            len=0.7
        )
    )

    return fig


# ============================================================
# 4. TABELA DE DETALHE COM COLUNAS CONFIGURADAS
# ============================================================

def render_tabela_detalhada(df: pd.DataFrame,
                            coluna_score: str = 'smart_score',
                            page_size: int = 50) -> None:
    """
    Renderiza tabela paginada com colunas configuradas para ordenação numérica correta.
    Inclui smart_score e classificacao_oportunidade.
    """
    display_cols = [
        'numero_imovel', 'cidade_normalizada', 'bairro_normalizado',
        'endereco_limpo' if 'endereco_limpo' in df.columns else 'endereco',
        'tipo_imovel', 'modalidade_venda',
        'preco', 'avaliacao', 'desconto_informado',
        coluna_score, 'area_privativa', 'quartos', 'banheiros', 'vagas',
        'financiavel', 'classificacao_oportunidade' if 'classificacao_oportunidade' in df.columns else 'faixa_preco'
    ]

    available_cols = [c for c in display_cols if c in df.columns]
    display_df = df[available_cols].copy()

    # Renomeia
    rename_map = {
        'numero_imovel': 'Nº Imóvel',
        'cidade_normalizada': 'Município',
        'bairro_normalizado': 'Bairro',
        'endereco_limpo': 'Logradouro',
        'endereco': 'Logradouro',
        'tipo_imovel': 'Tipo',
        'modalidade_venda': 'Modalidade',
        'preco': 'Preço',
        'avaliacao': 'Avaliação',
        'desconto_informado': 'Desc. Informado',
        'smart_score': 'Smart Score',
        'score_oportunidade': 'Score Antigo',
        'area_privativa': 'Área Priv.',
        'quartos': 'Qtos',
        'banheiros': 'Banhos',
        'vagas': 'Vagas',
        'financiavel': 'Financ.',
        'classificacao_oportunidade': 'Classificação',
        'faixa_preco': 'Faixa Preço'
    }
    display_df.columns = [rename_map.get(c, c) for c in available_cols]

    # Paginação
    total_pages = (len(display_df) - 1) // page_size + 1
    page = st.number_input("Página", 1, total_pages, 1, key="tbl_page")
    start = (page - 1) * page_size
    end = min(start + page_size, len(display_df))

    # Column config para ordenação numérica
    column_config = {
        "Preço": st.column_config.NumberColumn("Preço (R$)", format="R$ %.0f"),
        "Avaliação": st.column_config.NumberColumn("Avaliação (R$)", format="R$ %.0f"),
        "Desc. Informado": st.column_config.NumberColumn("Desc. Informado (%)", format="%.1f%%"),
        "Smart Score": st.column_config.NumberColumn("Smart Score", format="%.1f"),
        "Score Antigo": st.column_config.NumberColumn("Score Antigo", format="%.1f"),
        "Área Priv.": st.column_config.NumberColumn("Área (m²)", format="%.1f"),
        "Qtos": st.column_config.NumberColumn("Qtos", format="%d"),
        "Banhos": st.column_config.NumberColumn("Banhos", format="%d"),
        "Vagas": st.column_config.NumberColumn("Vagas", format="%d"),
        "Financ.": st.column_config.TextColumn("Financ."),
        "Classificação": st.column_config.TextColumn("Classificação"),
        "Faixa Preço": st.column_config.TextColumn("Faixa Preço"),
    }

    st.dataframe(
        display_df.iloc[start:end],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    st.caption(f"Mostrando {start + 1} a {end} de {len(display_df):,} registros")


# ============================================================
# 5. INTEGRAÇÃO NO APP.PY EXISTENTE
# ============================================================

def aplicar_melhorias_ux_no_app() -> str:
    """
    Retorna instruções de como integrar as melhorias no app.py existente.

    SUBSTITUA a função render_sidebar() por:
        from src.etl.dashboard.ux_improvements import render_sidebar_accordion
        filtered_df = render_sidebar_accordion(df)

    ADICIONE na aba Visão Geral (após KPIs):
        from src.etl.dashboard.ux_improvements import render_kpi_row_completa
        render_kpi_row_completa(filtered_df)

    SUBSTITUA plot_top_ruas() por:
        from src.etl.dashboard.ux_improvements import plot_top_logradouros_agrupados
        fig = plot_top_logradouros_agrupados(filtered_df, 15)

    SUBSTITUA render_table_tab() por:
        from src.etl.dashboard.ux_improvements import render_tabela_detalhada
        render_tabela_detalhada(filtered_df)
    """
    return """
# Instruções de Integração no app.py

## 1. Imports (topo do arquivo)
from src.etl.dashboard.ux_improvements import (
    render_sidebar_accordion,
    render_kpi_row_completa,
    plot_top_logradouros_agrupados,
    render_tabela_detalhada
)

## 2. Sidebar - SUBSTITUA render_sidebar(df) por:
filtered_df = render_sidebar_accordion(df)

## 3. Aba Visão Geral - SUBSTITUA bloco de KPIs por:
render_kpi_row_completa(filtered_df)

## 4. Gráfico Top Logradouros - SUBSTITUA plot_top_ruas por:
fig = plot_top_logradouros_agrupados(filtered_df, 15)
if fig: st.plotly_chart(fig, use_container_width=True)

## 5. Tabela Completa - SUBSTITUA render_table_tab por:
render_tabela_detalhada(filtered_df)
"""