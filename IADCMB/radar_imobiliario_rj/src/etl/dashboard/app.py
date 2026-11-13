"""
Dashboard Streamlit - Radar Imobiliário RJ
Executive dashboard com indicadores, mapa RJ, drill-down hierárquico e filtros interativos.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from src.utils.formatters import (
    format_brl, format_brl_compact, format_percent, format_number, format_int,
    get_brl_column_config, get_brl_compact_column_config, get_percent_column_config, get_number_column_config
)


# ============================================================
# Configuração da Página
# ============================================================
st.set_page_config(
    page_title="Radar Imobiliário RJ",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .drilldown-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .drilldown-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .drilldown-metric {
        font-size: 1.5rem;
        font-weight: 700;
        color: #3b82f6;
    }
    .drilldown-sub {
        font-size: 0.8rem;
        color: #6b7280;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    .map-container {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Coordenadas dos Municípios do RJ (lat, lon)
# ============================================================
RJ_MUNICIPIOS_COORDS = {
    'RIO DE JANEIRO': (-22.9068, -43.1729),
    'NITEROI': (-22.8833, -43.1036),
    'SAO GONCALO': (-22.8269, -43.0539),
    'DUQUE DE CAXIAS': (-22.7856, -43.3117),
    'NOVA IGUACU': (-22.7592, -43.4511),
    'BELFORD ROXO': (-22.7639, -43.3994),
    'SAO JOAO DE MERITI': (-22.8039, -43.3722),
    'CAMPOS DOS GOYTACAZES': (-21.7539, -41.3239),
    'PETROPOLIS': (-22.5069, -43.1781),
    'VOLTA REDONDA': (-22.5239, -44.1039),
    'MACAE': (-22.3708, -41.7869),
    'CABO FRIO': (-22.8794, -42.0186),
    'ANGRA DOS REIS': (-23.0067, -44.3181),
    'TERESOPOLIS': (-22.4122, -42.9783),
    'NOVA FRIBURGO': (-22.2819, -42.5311),
    'BARRA MANSA': (-22.5442, -44.1717),
    'RESENDE': (-22.4689, -44.4467),
    'QUEIMADOS': (-22.7183, -43.5553),
    'JAPERI': (-22.6431, -43.6539),
    'MESQUITA': (-22.7844, -43.4278),
    'NILÓPOLIS': (-22.8072, -43.4139),
    'ITABORAI': (-22.7444, -42.8589),
    'SAO PEDRO DA ALDEIA': (-22.8392, -42.1028),
    'MAGÉ': (-22.6528, -43.0408),
    'ITAGUAÍ': (-22.8542, -43.7783),
    'RIO BONITO': (-22.7036, -42.6053),
    'SILVA JARDIM': (-22.6508, -42.3917),
    'CACHOEIRAS DE MACACU': (-22.4639, -42.6589),
    'GUAPIMIRIM': (-22.5419, -42.9819),
    'TANGUÁ': (-22.7292, -42.7144),
    'RIO DAS OSTRAS': (-22.5281, -41.9450),
    'CASIMIRO DE ABREU': (-22.4817, -42.2028),
    'QUISSAMÃ': (-22.1158, -41.4717),
    'CARAPEBUS': (-22.1564, -41.5597),
    'CONCEIÇÃO DE MACABU': (-22.0875, -41.8739),
    'MACAÉ': (-22.3708, -41.7869),
    'SÃO FRANCISCO DE ITABAPOANA': (-21.4667, -41.1167),
    'SÃO JOÃO DA BARRA': (-21.6389, -41.0500),
    'ITAPERUNA': (-21.2050, -41.8878),
    'SANTO ANTONIO DE PADUA': (-21.5689, -42.1800),
    'CAMBUCI': (-21.5639, -41.9319),
    'ARUJA': (-21.8208, -42.1489),
    'MIRAI': (-21.1200, -42.6169),
    'PATY DO ALFERES': (-22.4189, -43.4228),
    'MENDES': (-22.5322, -43.7406),
    'VASSOURAS': (-22.4069, -43.6631),
    'BARRA DO PIRAI': (-22.4697, -43.8267),
    'PINHEIRAL': (-22.5183, -44.0000),
    'RIO CLARO': (-22.7189, -44.1369),
    'PARACAMBI': (-22.6078, -43.7078),
    'ENGENHEIRO PAULO DE FRONTIN': (-22.5967, -43.6861),
    'MIGUEL PEREIRA': (-22.4528, -43.4678),
    'PARAÍBA DO SUL': (-22.1583, -43.2939),
    'TRÊS RIOS': (-22.1167, -43.2089),
    'LEVY GASPARIAN': (-22.0989, -43.2275),
    'AREAL': (-22.1553, -43.1053),
    'SAPUCAIA': (-22.0839, -43.0158),
    'CARAMBEI': (-21.5739, -43.2861),
    'SUMIDOURO': (-21.9772, -42.7450),
    'CARMO': (-21.9350, -42.6119),
    'CANTAGALO': (-21.9758, -42.3689),
    'CORDEIRO': (-21.9589, -42.3172),
    'DUAS BARRAS': (-22.0528, -42.3706),
    'SÃO SEBASTIÃO DO ALTO': (-21.9361, -42.1422),
    'MACUCO': (-21.8747, -42.1014),
    'TRAJANO DE MORAES': (-21.9533, -42.0839),
    'SANTA MARIA MADALENA': (-21.9650, -41.9589),
    'BOM JESUS DO ITABAPOANA': (-21.1358, -41.6789),
    'ITALVA': (-21.3453, -41.7775),
    'CARDOSO MOREIRA': (-21.5031, -41.5175),
    'LARANJAL': (-21.4803, -42.3614),
    'NATIVIDADE': (-21.0439, -41.9639),
    'PORCIUNCULA': (-21.0017, -42.0558),
    'TOME': (-21.0472, -41.8731),
    'VARRE-SAI': (-20.9453, -41.8875),
}

# Coordenadas centro do RJ para fallback
RJ_CENTER = (-22.9068, -43.1729)


# ============================================================
# Cache de Dados
# ============================================================
@st.cache_data(ttl=300, show_spinner="Carregando dados processados...")
def load_latest_data():
    """Carrega o último snapshot processado (Parquet)."""
    processed_dir = Path("data/processed")
    latest_parquet = processed_dir / "imoveis_rj_latest.parquet"
    if latest_parquet.exists():
        return pd.read_parquet(latest_parquet)
    parquet_files = list(processed_dir.glob("imoveis_rj_snapshot_*.parquet"))
    if parquet_files:
        latest = max(parquet_files, key=lambda f: f.stat().st_mtime)
        return pd.read_parquet(latest)
    return pd.DataFrame()


@st.cache_data(ttl=300)
def get_municipio_coords(municipio):
    """Retorna coordenadas do município ou centro do RJ."""
    municipio_upper = municipio.upper()
    return RJ_MUNICIPIOS_COORDS.get(municipio_upper, RJ_CENTER)


# ============================================================
# Funções de Gráficos Principais (mantidos: Tipo, Modalidade, Top Municípios)
# ============================================================
def plot_tipo_imovel(df):
    """Distribuição por tipo de imóvel - Bar chart."""
    counts = df['tipo_imovel'].value_counts().reset_index()
    counts.columns = ['Tipo', 'Quantidade']

    fig = px.bar(
        counts, x='Tipo', y='Quantidade',
        color='Tipo',
        color_discrete_sequence=px.colors.qualitative.Set2,
        text='Quantidade'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title=None,
        yaxis_title="Quantidade"
    )
    return fig


def plot_modalidade(df):
    """Distribuição por modalidade de venda - Bar chart."""
    counts = df['modalidade_venda'].value_counts().reset_index()
    counts.columns = ['Modalidade', 'Quantidade']

    fig = px.bar(
        counts, x='Modalidade', y='Quantidade',
        color='Modalidade',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        text='Quantidade'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title=None,
        yaxis_title="Quantidade"
    )
    return fig


def plot_top_municipios(df, top_n=15):
    """Top N municípios - Horizontal bar chart."""
    counts = df['cidade_normalizada'].value_counts().head(top_n).reset_index()
    counts.columns = ['Município', 'Quantidade']
    counts = counts.sort_values('Quantidade', ascending=True)

    fig = px.bar(
        counts, x='Quantidade', y='Município',
        orientation='h',
        color='Quantidade',
        color_continuous_scale='Blues',
        text='Quantidade'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        showlegend=False,
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Quantidade",
        yaxis_title=None
    )
    return fig


def plot_top_bairros(df, top_n=15):
    """Top N bairros - Horizontal bar chart."""
    counts = df['bairro_normalizado'].value_counts().head(top_n).reset_index()
    counts.columns = ['Bairro', 'Quantidade']
    counts = counts.sort_values('Quantidade', ascending=True)

    fig = px.bar(
        counts, x='Quantidade', y='Bairro',
        orientation='h',
        color='Quantidade',
        color_continuous_scale='Greens',
        text='Quantidade'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        showlegend=False,
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Quantidade",
        yaxis_title=None
    )
    return fig


def plot_top_ruas(df, top_n=15):
    """Top N logradouros - Horizontal bar chart com média de preço."""
    if 'endereco' not in df.columns:
        return None

    # Agrupa por logradouro: quantidade + média de preço
    rua_stats = df.groupby('endereco').agg(
        Quantidade=('numero_imovel', 'count'),
        Preco_Medio=('preco', 'mean')
    ).sort_values('Quantidade', ascending=False).head(top_n).reset_index()

    rua_stats = rua_stats.sort_values('Quantidade', ascending=True)

    # Formata preço médio para hover (padrão brasileiro)
    rua_stats['Preco_Medio_Fmt'] = rua_stats['Preco_Medio'].apply(format_brl_compact)

    fig = px.bar(
        rua_stats, x='Quantidade', y='endereco',
        orientation='h',
        color='Preco_Medio',
        color_continuous_scale='Oranges',
        text='Quantidade',
        hover_data={
            'Quantidade': True,
            'Preco_Medio': False,
            'Preco_Medio_Fmt': True
        }
    )
    fig.update_traces(
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Quantidade: %{x}<br>Preço Médio: %{customdata[0]}<extra></extra>'
    )
    fig.update_layout(
        showlegend=False,
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Quantidade de Imóveis",
        yaxis_title=None,
        coloraxis_colorbar=dict(
            title="Preço Médio (R$)",
            thickness=15,
            len=0.7
        )
    )
    return fig


# ============================================================
# Mapa do RJ
# ============================================================
def create_rj_map(df):
    """Cria mapa scatter_geo do RJ com quantitativo por município."""
    # Agrega por município
    muni_stats = df.groupby('cidade_normalizada').agg(
        qtd=('numero_imovel', 'count'),
        preco_medio=('preco', 'mean'),
        preco_mediano=('preco', 'median'),
        desconto_medio=('desconto_informado', 'mean'),
        score_medio=('score_oportunidade', 'mean')
    ).reset_index()

    # Adiciona coordenadas
    muni_stats['lat'] = muni_stats['cidade_normalizada'].apply(lambda x: get_municipio_coords(x)[0])
    muni_stats['lon'] = muni_stats['cidade_normalizada'].apply(lambda x: get_municipio_coords(x)[1])

    # Tamanho do bubble baseado na quantidade (escala raiz quadrada para melhor visualização)
    muni_stats['size'] = (muni_stats['qtd'] ** 0.5) * 3
    muni_stats['size'] = muni_stats['size'].clip(lower=8, upper=50)

    # Adiciona colunas formatadas para hover (padrão brasileiro)
    muni_stats['preco_medio_fmt'] = muni_stats['preco_medio'].apply(format_brl_compact)
    muni_stats['preco_mediano_fmt'] = muni_stats['preco_mediano'].apply(format_brl_compact)
    muni_stats['desconto_medio_fmt'] = muni_stats['desconto_medio'].apply(lambda x: format_percent(x, 1))
    muni_stats['score_medio_fmt'] = muni_stats['score_medio'].apply(lambda x: format_number(x, 1))

    # Cor baseada no desconto médio (sequencial)
    fig = px.scatter_geo(
        muni_stats,
        lat='lat',
        lon='lon',
        size='size',
        color='desconto_medio',
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=30,
        hover_name='cidade_normalizada',
        hover_data={
            'qtd': True,
            'preco_medio': False,
            'preco_mediano': False,
            'desconto_medio': False,
            'score_medio': False,
            'preco_medio_fmt': True,
            'preco_mediano_fmt': True,
            'desconto_medio_fmt': True,
            'score_medio_fmt': True,
            'lat': False,
            'lon': False,
            'size': False
        },
        scope='south america',
        height=600,
    )

    fig.update_geos(
        showcountries=False,
        showcoastlines=True,
        coastlinecolor="LightGray",
        showland=True,
        landcolor="white",
        showocean=True,
        oceancolor="LightBlue",
        showlakes=True,
        lakecolor="LightBlue",
        showrivers=True,
        rivercolor="LightBlue",
        fitbounds="locations",
        center=dict(lat=-22.5, lon=-43.0),
        projection_scale=12,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            title="Desconto Médio (%)",
            thickness=15,
            len=0.7
        ),
    )

    return fig, muni_stats


# ============================================================
# Drill-down Hierárquico
# ============================================================
def render_drilldown_section(df, level='municipio'):
    """Renderiza seção de drill-down hierárquico."""

    if level == 'municipio':
        # Nível 1: Municípios
        st.subheader("🏙️ Nível 1: Municípios")

        muni_stats = df.groupby('cidade_normalizada').agg(
            Qtd=('numero_imovel', 'count'),
            Preço_Médio=('preco', 'mean'),
            Preço_Mediano=('preco', 'median'),
            Desconto_Médio=('desconto_informado', 'mean'),
            Score_Médio=('score_oportunidade', 'mean'),
            Financiáveis=('financiavel', 'sum')
        ).sort_values('Qtd', ascending=False).reset_index()

        muni_stats['Financiáveis_Pct'] = (muni_stats['Financiáveis'] / muni_stats['Qtd'] * 100).round(1)

        # Formatação usando utilitários brasileiros
        muni_stats['Preço_Médio'] = muni_stats['Preço_Médio'].apply(format_brl_compact)
        muni_stats['Preço_Mediano'] = muni_stats['Preço_Mediano'].apply(format_brl_compact)
        muni_stats['Desconto_Médio'] = muni_stats['Desconto_Médio'].apply(lambda x: format_percent(x, 1))
        muni_stats['Score_Médio'] = muni_stats['Score_Médio'].apply(lambda x: format_number(x, 1))

        muni_stats.columns = ['Município', 'Qtd', 'Preço Médio', 'Preço Mediana', 'Desc. Médio', 'Score Médio', 'Financ.', '% Financ.']

        st.dataframe(
            muni_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Qtd": get_number_column_config("Qtd", 0),
                "% Financ.": get_percent_column_config("% Financ.", 1),
            }
        )

        # Selectbox para drill-down
        municipios = ['Selecione um município...'] + sorted(df['cidade_normalizada'].dropna().unique().tolist())
        selected_muni = st.selectbox("🔍 Drill-down → Selecione o município:", municipios, key="drill_muni")

        if selected_muni != 'Selecione um município...':
            st.session_state['drill_municipio'] = selected_muni
            return 'bairro', selected_muni

    elif level == 'bairro':
        municipio = st.session_state.get('drill_municipio', 'RIO DE JANEIRO')
        st.subheader(f"🏘️ Nível 2: Bairros — {municipio}")

        df_muni = df[df['cidade_normalizada'] == municipio]

        bairro_stats = df_muni.groupby('bairro_normalizado').agg(
            Qtd=('numero_imovel', 'count'),
            Preço_Médio=('preco', 'mean'),
            Preço_Mediano=('preco', 'median'),
            Desconto_Médio=('desconto_informado', 'mean'),
            Score_Médio=('score_oportunidade', 'mean'),
            Financiáveis=('financiavel', 'sum')
        ).sort_values('Qtd', ascending=False).reset_index()

        bairro_stats['Financiáveis_Pct'] = (bairro_stats['Financiáveis'] / bairro_stats['Qtd'] * 100).round(1)
        bairro_stats['Preço_Médio'] = bairro_stats['Preço_Médio'].apply(format_brl_compact)
        bairro_stats['Preço_Mediano'] = bairro_stats['Preço_Mediano'].apply(format_brl_compact)
        bairro_stats['Desconto_Médio'] = bairro_stats['Desconto_Médio'].apply(lambda x: format_percent(x, 1))
        bairro_stats['Score_Médio'] = bairro_stats['Score_Médio'].apply(lambda x: format_number(x, 1))

        bairro_stats.columns = ['Bairro', 'Qtd', 'Preço Médio', 'Preço Mediana', 'Desc. Médio', 'Score Médio', 'Financ.', '% Financ.']

        st.dataframe(
            bairro_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Qtd": get_number_column_config("Qtd", 0),
                "% Financ.": get_percent_column_config("% Financ.", 1),
            }
        )

        # Selectbox para drill-down
        bairros = ['Selecione um bairro...'] + sorted(df_muni['bairro_normalizado'].dropna().unique().tolist())
        selected_bairro = st.selectbox("🔍 Drill-down → Selecione o bairro:", bairros, key="drill_bairro")

        if selected_bairro != 'Selecione um bairro...':
            return 'rua', {'municipio': municipio, 'bairro': selected_bairro}

    elif level == 'rua':
        context = st.session_state.get('drill_context', {})
        municipio = context.get('municipio', '')
        bairro = context.get('bairro', '')
        st.subheader(f"🛣️ Nível 3: Logradouros — {municipio} / {bairro}")

        df_bairro = df[
            (df['cidade_normalizada'] == municipio) &
            (df['bairro_normalizado'] == bairro)
        ]

        if 'endereco' in df_bairro.columns:
            rua_stats = df_bairro.groupby('endereco').agg(
                Qtd=('numero_imovel', 'count'),
                Preço_Médio=('preco', 'mean'),
                Preço_Mediano=('preco', 'median'),
                Desconto_Médio=('desconto_informado', 'mean'),
                Score_Médio=('score_oportunidade', 'mean'),
                Financiáveis=('financiavel', 'sum')
            ).sort_values('Qtd', ascending=False).reset_index()

            rua_stats['Financiáveis_Pct'] = (rua_stats['Financiáveis'] / rua_stats['Qtd'] * 100).round(1)
            rua_stats['Preço_Médio'] = rua_stats['Preço_Médio'].apply(format_brl_compact)
            rua_stats['Preço_Mediano'] = rua_stats['Preço_Mediano'].apply(format_brl_compact)
            rua_stats['Desconto_Médio'] = rua_stats['Desconto_Médio'].apply(lambda x: format_percent(x, 1))
            rua_stats['Score_Médio'] = rua_stats['Score_Médio'].apply(lambda x: format_number(x, 1))

            rua_stats.columns = ['Logradouro', 'Qtd', 'Preço Médio', 'Preço Mediana', 'Desc. Médio', 'Score Médio', 'Financ.', '% Financ.']

            st.dataframe(
                rua_stats,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Qtd": get_number_column_config("Qtd", 0),
                    "% Financ.": get_percent_column_config("% Financ.", 1),
                }
            )

            # Detalhe dos imóveis na rua selecionada
            st.markdown("---")
            st.subheader("🏠 Imóveis neste Logradouro")

            logradouros = ['Todos'] + sorted(df_bairro['endereco'].dropna().unique().tolist())
            selected_rua = st.selectbox("Filtrar logradouro:", logradouros, key="drill_rua")

            if selected_rua != 'Todos':
                df_rua = df_bairro[df_bairro['endereco'] == selected_rua]
            else:
                df_rua = df_bairro

            # Tabela detalhada dos imóveis
            detail_cols = ['numero_imovel', 'tipo_imovel', 'modalidade_venda', 'preco', 'avaliacao',
                          'desconto_informado', 'score_oportunidade', 'area_privativa',
                          'quartos', 'banheiros', 'vagas', 'financiavel']

            detail_df = df_rua[detail_cols].copy()
            detail_df['preco'] = detail_df['preco'].apply(format_brl_compact)
            detail_df['avaliacao'] = detail_df['avaliacao'].apply(format_brl_compact)
            detail_df['desconto_informado'] = detail_df['desconto_informado'].apply(lambda x: format_percent(x, 1))
            detail_df['score_oportunidade'] = detail_df['score_oportunidade'].apply(lambda x: format_number(x, 1))
            detail_df['financiavel'] = detail_df['financiavel'].map({True: '✅', False: '❌'})

            detail_df.columns = ['Nº Imóvel', 'Tipo', 'Modalidade', 'Preço', 'Avaliação',
                               'Desc. Informado', 'Score', 'Área Priv.', 'Qtos', 'Banhos', 'Vagas', 'Financ.']

            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        else:
            st.info("Coluna 'endereco' não disponível para drill-down até rua.")

    return None, None


# ============================================================
# Sidebar - Filtros
# ============================================================
def render_sidebar(df):
    """Renderiza sidebar com filtros cascata."""
    st.sidebar.markdown("## 🔍 Filtros")

    # Filtro por Município
    municipios = ['Todos'] + sorted(df['cidade_normalizada'].dropna().unique().tolist())
    municipio_sel = st.sidebar.selectbox("Município", municipios, index=0, key="filter_municipio")

    # Filtro por Bairro (cascata - depende do município)
    if municipio_sel != 'Todos':
        df_muni = df[df['cidade_normalizada'] == municipio_sel]
        bairros = ['Todos'] + sorted(df_muni['bairro_normalizado'].dropna().unique().tolist())
    else:
        bairros = ['Todos'] + sorted(df['bairro_normalizado'].dropna().unique().tolist())
    bairro_sel = st.sidebar.selectbox("Bairro", bairros, index=0, key="filter_bairro")

    # Filtro por Logradouro/Rua (cascata - depende do bairro)
    if bairro_sel != 'Todos' and municipio_sel != 'Todos':
        df_bairro = df[(df['cidade_normalizada'] == municipio_sel) & (df['bairro_normalizado'] == bairro_sel)]
        ruas = ['Todos'] + sorted(df_bairro['endereco'].dropna().unique().tolist()) if 'endereco' in df_bairro.columns else ['Todos']
    elif bairro_sel != 'Todos':
        df_bairro = df[df['bairro_normalizado'] == bairro_sel]
        ruas = ['Todos'] + sorted(df_bairro['endereco'].dropna().unique().tolist()) if 'endereco' in df_bairro.columns else ['Todos']
    else:
        ruas = ['Todos'] + sorted(df['endereco'].dropna().unique().tolist()) if 'endereco' in df.columns else ['Todos']
    rua_sel = st.sidebar.selectbox("Logradouro/Rua", ruas, index=0, key="filter_rua")

    # Filtro por Tipo de Imóvel
    tipos = ['Todos'] + sorted(df['tipo_imovel'].dropna().unique().tolist())
    tipo_sel = st.sidebar.selectbox("Tipo de Imóvel", tipos, index=0, key="filter_tipo")

    # Filtro por Modalidade
    modalidades = ['Todas'] + sorted(df['modalidade_venda'].dropna().unique().tolist())
    modalidade_sel = st.sidebar.selectbox("Modalidade de Venda", modalidades, index=0, key="filter_modalidade")

    # Filtro por Faixa de Preço
    faixas_preco = ['Todas'] + sorted(df['faixa_preco'].dropna().unique().tolist())
    faixa_preco_sel = st.sidebar.selectbox("Faixa de Preço", faixas_preco, index=0, key="filter_faixa_preco")

    # Filtro por Faixa de Desconto
    faixas_desc = ['Todas'] + sorted(df['faixa_desconto'].dropna().unique().tolist())
    faixa_desc_sel = st.sidebar.selectbox("Faixa de Desconto", faixas_desc, index=0, key="filter_faixa_desc")

    # Filtro Financiável
    financ_sel = st.sidebar.selectbox("Financiável", ['Todos', 'Sim', 'Não'], index=0, key="filter_financ")

    # Filtro Score mínimo
    score_min = st.sidebar.slider("Score Mínimo", 0, 100, 0, 5, key="filter_score")

    # Filtro Preço (range)
    preco_min = float(df['preco'].min())
    preco_max = float(df['preco'].max())
    preco_range = st.sidebar.slider(
        "Faixa de Preço (R$)",
        preco_min, preco_max,
        (preco_min, preco_max),
        step=10000.0,
        format="R$ %.0f",
        key="filter_preco_range"
    )

    # Aplica filtros
    filtered = df.copy()

    if municipio_sel != 'Todos':
        filtered = filtered[filtered['cidade_normalizada'] == municipio_sel]
    if bairro_sel != 'Todos':
        filtered = filtered[filtered['bairro_normalizado'] == bairro_sel]
    if rua_sel != 'Todos':
        filtered = filtered[filtered['endereco'] == rua_sel]
    if tipo_sel != 'Todos':
        filtered = filtered[filtered['tipo_imovel'] == tipo_sel]
    if modalidade_sel != 'Todas':
        filtered = filtered[filtered['modalidade_venda'] == modalidade_sel]
    if faixa_preco_sel != 'Todas':
        filtered = filtered[filtered['faixa_preco'] == faixa_preco_sel]
    if faixa_desc_sel != 'Todas':
        filtered = filtered[filtered['faixa_desconto'] == faixa_desc_sel]
    if financ_sel == 'Sim':
        filtered = filtered[filtered['financiavel'] == True]
    elif financ_sel == 'Não':
        filtered = filtered[filtered['financiavel'] == False]
    if score_min > 0:
        filtered = filtered[filtered['score_oportunidade'] >= score_min]

    filtered = filtered[
        (filtered['preco'] >= preco_range[0]) &
        (filtered['preco'] <= preco_range[1])
    ]

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Registros filtrados:** {len(filtered):,} / {len(df):,}")

    # Armazena contexto para drill-down
    filtered.attrs['drill_municipio'] = municipio_sel if municipio_sel != 'Todos' else 'RIO DE JANEIRO'
    filtered.attrs['drill_context'] = {'municipio': municipio_sel, 'bairro': bairro_sel}

    return filtered


# ============================================================
# Aba: Visão Geral (KPIs + Gráficos Principais - apenas os mantidos)
# ============================================================
def render_overview_tab(df):
    """Aba Visão Geral com KPIs e gráficos principais."""

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Imóveis", format_int(len(df)))

    with col2:
        preco_medio = df['preco'].mean()
        st.metric("Preço Médio", format_brl_compact(preco_medio))

    with col3:
        desconto_medio = df['desconto_informado'].mean()
        st.metric("Desconto Médio", format_percent(desconto_medio))

    with col4:
        score_medio = df['score_oportunidade'].mean()
        st.metric("Score Médio", format_number(score_medio, 1))

    with col5:
        financiaveis_pct = (df['financiavel'].sum() / len(df)) * 100
        st.metric("% Financiáveis", format_percent(financiaveis_pct))

    st.markdown("")

    # Gráficos principais - apenas os mantidos: Tipo, Modalidade, Top Municípios
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("📊 Distribuição por Tipo de Imóvel")
        st.plotly_chart(plot_tipo_imovel(df), use_container_width=True)

    with row1_col2:
        st.subheader("📊 Distribuição por Modalidade")
        st.plotly_chart(plot_modalidade(df), use_container_width=True)

    st.markdown("---")
    st.subheader("🏙️ Top 15 Municípios")
    st.plotly_chart(plot_top_municipios(df, 15), use_container_width=True)

    st.markdown("---")
    # Novos gráficos: Top Bairros e Top Ruas
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("🏘️ Top 15 Bairros")
        st.plotly_chart(plot_top_bairros(df, 15), use_container_width=True)

    with row2_col2:
        st.subheader("🛣️ Top 15 Logradouros")
        rua_fig = plot_top_ruas(df, 15)
        if rua_fig:
            st.plotly_chart(rua_fig, use_container_width=True)
        else:
            st.info("Coluna 'endereco' não disponível para gráfico de logradouros.")


# ============================================================
# Aba: Mapa RJ + Drill-down
# ============================================================
def render_map_drilldown_tab(df):
    """Aba Mapa do RJ + Drill-down hierárquico."""

    # Mapa
    st.subheader("🗺️ Mapa do Rio de Janeiro - Quantitativo por Município")
    st.caption("Tamanho do círculo = quantidade de imóveis | Cor = desconto médio (%)")

    map_fig, muni_stats = create_rj_map(df)
    st.plotly_chart(map_fig, use_container_width=True)

    st.markdown("---")

    # Drill-down hierárquico
    st.subheader("🔍 Drill-down Hierárquico: Estado → Município → Bairro → Logradouro")

    # Inicializa estado do drill-down
    if 'drill_level' not in st.session_state:
        st.session_state['drill_level'] = 'municipio'

    # Botões de navegação
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 4])
    with nav_col1:
        if st.button("🔙 Voltar Nível", disabled=st.session_state['drill_level'] == 'municipio'):
            if st.session_state['drill_level'] == 'bairro':
                st.session_state['drill_level'] = 'municipio'
            elif st.session_state['drill_level'] == 'rua':
                st.session_state['drill_level'] = 'bairro'
            st.rerun()

    with nav_col2:
        if st.button("🏠 Resetar"):
            st.session_state['drill_level'] = 'municipio'
            st.rerun()

    st.markdown("")

    # Renderiza nível atual
    if st.session_state['drill_level'] == 'municipio':
        next_level, context = render_drilldown_section(df, 'municipio')
        if next_level:
            st.session_state['drill_level'] = next_level
            if context:
                df.attrs['drill_context'] = context
            st.rerun()

    elif st.session_state['drill_level'] == 'bairro':
        next_level, context = render_drilldown_section(df, 'bairro')
        if next_level:
            st.session_state['drill_level'] = next_level
            if context:
                df.attrs['drill_context'] = context
            st.rerun()

    elif st.session_state['drill_level'] == 'rua':
        render_drilldown_section(df, 'rua')


# ============================================================
# Aba: Tabela Completa
# ============================================================
def render_table_tab(df):
    """Aba com tabela completa paginada e exportável."""

    st.subheader("📋 Tabela Completa de Imóveis")

    # Colunas para exibição
    display_cols = [
        'numero_imovel', 'cidade_normalizada', 'bairro_normalizado', 'endereco', 'tipo_imovel',
        'modalidade_venda', 'preco', 'avaliacao', 'desconto_informado',
        'desconto_calculado', 'score_oportunidade', 'area_privativa',
        'quartos', 'banheiros', 'vagas', 'financiavel', 'faixa_preco', 'faixa_desconto'
    ]

    # Filtra apenas colunas que existem
    available_cols = [c for c in display_cols if c in df.columns]

    display_df = df[available_cols].copy()

    # Renomeia colunas para exibição (mantém valores numéricos para ordenação)
    display_df.columns = [
        'Nº Imóvel', 'Município', 'Bairro', 'Logradouro', 'Tipo', 'Modalidade',
        'Preço', 'Avaliação', 'Desc. Informado', 'Desc. Calculado',
        'Score', 'Área Priv.', 'Qtos', 'Banhos', 'Vagas', 'Financ.',
        'Faixa Preço', 'Faixa Desc.'
    ][:len(available_cols)]

    # Paginação
    page_size = st.selectbox("Linhas por página", [25, 50, 100, 200], index=1, key="table_page_size")
    total_pages = (len(display_df) - 1) // page_size + 1
    page = st.number_input("Página", 1, total_pages, 1, key="table_page")

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(display_df))

    # Configuração de colunas para formatação numérica correta (permite ordenação por valor)
    column_config = {
        "Preço": st.column_config.NumberColumn("Preço (R$)", format="R$ %.0f"),
        "Avaliação": st.column_config.NumberColumn("Avaliação (R$)", format="R$ %.0f"),
        "Desc. Informado": st.column_config.NumberColumn("Desc. Informado (%)", format="%.1f%%"),
        "Desc. Calculado": st.column_config.NumberColumn("Desc. Calculado (%)", format="%.1f%%"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f"),
        "Área Priv.": st.column_config.NumberColumn("Área Priv. (m²)", format="%.1f"),
        "Qtos": st.column_config.NumberColumn("Qtos", format="%d"),
        "Banhos": st.column_config.NumberColumn("Banhos", format="%d"),
        "Vagas": st.column_config.NumberColumn("Vagas", format="%d"),
        "Financ.": st.column_config.TextColumn("Financ."),
        "Faixa Preço": st.column_config.TextColumn("Faixa Preço"),
        "Faixa Desc.": st.column_config.TextColumn("Faixa Desc."),
    }

    st.dataframe(
        display_df.iloc[start_idx:end_idx],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    st.caption(f"Mostrando {start_idx + 1} a {end_idx} de {len(display_df):,} registros")

    # Botão de download CSV
    csv = df[available_cols].to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button(
        label="📥 Baixar CSV Completo",
        data=csv,
        file_name=f"radar_imobiliario_rj_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


# ============================================================
# Main App
# ============================================================
def main():
    # Header
    st.markdown('<div class="main-header">🏠 Radar Imobiliário RJ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Plataforma de Inteligência Imobiliária - Caixa Econômica Federal</div>', unsafe_allow_html=True)

    # Carrega dados
    df = load_latest_data()

    if df.empty:
        st.error("❌ Nenhum dado encontrado. Execute o pipeline ETL primeiro:")
        st.code("python main.py --force")
        st.stop()

    # Sidebar com filtros
    filtered_df = render_sidebar(df)

    # Tabs principais (reduzidas para 3)
    tab1, tab2, tab3 = st.tabs([
        "📊 Visão Geral",
        "🗺️ Mapa RJ + Drill-down",
        "📋 Tabela Completa"
    ])

    with tab1:
        render_overview_tab(filtered_df)

    with tab2:
        render_map_drilldown_tab(filtered_df)

    with tab3:
        render_table_tab(filtered_df)

    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"Última atualização: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
    with col2:
        st.caption(f"Registros exibidos: {len(filtered_df):,} / {len(df):,}")
    with col3:
        st.caption("Radar Imobiliário RJ v1.0 | Pipeline ETL + Dashboard + Mapa + Drill-down")


if __name__ == "__main__":
    main()