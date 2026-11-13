# Guia de Integração - Melhorias Radar Imobiliário RJ

Este documento explica como integrar os três módulos de melhoria no seu código existente.

---

## 1. ETL Upsert/Sync (`src/etl/sync.py`)

### O que faz:
- Cria tabela `catalogo_imoveis` com estado atual (ativo/removido)
- Implementa Upsert limpo por `id_imovel` (numero_imovel)
- Marca como removido imóveis que não aparecem na raspagem atual
- Agrupa logradouros via `endereco_limpo` (remove nº apto/bloco)

### Integração no `pipeline.py`:

```python
# 1. Adicione import no topo
from src.etl.sync import sincronizar_catalogo

# 2. No método executar(), APÓS a validação (etapa 3) e ANTES do salvamento (etapa 4):
#    Adicione a sincronização do catálogo

# No arquivo pipeline.py, linha ~135, depois de:
# self.relatorio_qualidade = self.validator.validar_dataframe(self.df_processado)

# ADICIONE:
self.logger.info("ETAPA 3.5: Sincronização do catálogo (Upsert)...")
resultado_sync = sincronizar_catalogo(self.df_processado, self.snapshot_id)
self.logger.info(
    f"  → Inseridos: {resultado_sync['inseridos']:,} | "
    f"Atualizados: {resultado_sync['atualizados']:,} | "
    f"Removidos: {resultado_sync['removidos']:,} | "
    f"Inalterados: {resultado_sync['inalterados']:,}"
)

# 3. Opcional: Salve estatísticas do catálogo no metadata do snapshot
snapshot_meta['catalogo_stats'] = resultado_sync
```

### Uso posterior (dashboard, relatórios):
```python
from src.etl.sync import CatalogoSync

sync = CatalogoSync()
df_catalogo = sync.obter_catalogo_ativo()  # Apenas ativos
stats = sync.obter_estatisticas_catalogo()  # KPIs incluindo Gold
logradouros = sync.obter_logradouros_agrupados(top_n=15)
```

---

## 2. Smart Score (`src/etl/smart_score.py`)

### O que faz:
- Substitui `score_oportunidade` por `smart_score` (0-100)
- 5 componentes ponderados:
  1. Desconto 35% (normalizado até 60%)
  2. Liquidez Regional 25% (bairros mapeados do RJ)
  3. Financiamento 20% (Sim=1.0, Não=0.2)
  4. Modalidade 10% (Direta=1.0, Leilão=0.7, Licitação=0.5)
  5. Tipo 10% (Apto=1.0, Casa=0.8, Terreno=0.5)
- Adiciona `classificacao_oportunidade` (Gold/Silver/Bronze/Regular)
- Função `contar_oportunidades_gold()` para KPI

### Integração no `transform.py` (opção A - substituir método):

```python
# No topo do transform.py, adicione:
from src.etl.smart_score import (
    calcular_smart_score,
    aplicar_smart_score,
    adicionar_classificacao_oportunidade,
    enriquecer_com_smart_score
)

# No DataTransformer, SUBSTITUA _calcular_score_oportunidade por:
def _calcular_score_oportunidade(self, imovel) -> float:
    """Novo Smart Score composto."""
    row = pd.Series(imovel.to_dict())
    return calcular_smart_score(row)

# No método transform(), APÓS criar df_proc (linha ~293), ADICIONE:
self.df_processado = enriquecer_com_smart_score(df_proc)
# Isso adiciona smart_score E classificacao_oportunidade
```

### Integração no `pipeline.py` (opção B - pós-transformação):

```python
# No pipeline.py, depois de:
# self.df_processado = self.transformer.transform(self.df_raw, self.snapshot_id)

# ADICIONE:
from src.etl.smart_score import enriquecer_com_smart_score
self.df_processado = enriquecer_com_smart_score(self.df_processado)
self.logger.info(f"  → Smart Score aplicado (média: {self.df_processado['smart_score'].mean():.1f})")
```

### Atualização do schema (`schemas.py`):
```python
# Em ImovelProcessado, adicione:
smart_score: Optional[float] = None
classificacao_oportunidade: Optional[str] = None

# Em COLUNAS_PROCESSADO, adicione no final:
'smart_score', 'classificacao_oportunidade'
```

---

## 3. Dashboard UX (`src/etl/dashboard/ux_improvements.py`)

### O que faz:
- **Sidebar Accordion**: 3 menus colapsáveis (Localização, Atributos, Comerciais)
- **KPI Gold**: Card destacado para oportunidades (Score>80, Desc>50%, Financiável)
- **Top Logradouros Agrupados**: Usa `endereco_limpo` para agrupar rua/condomínio
- **Tabela Detalhada**: Com `smart_score` e `classificacao_oportunidade`

### Integração no `app.py`:

```python
# 1. Imports (topo, após imports existentes)
from src.etl.dashboard.ux_improvements import (
    render_sidebar_accordion,
    render_kpi_row_completa,
    plot_top_logradouros_agrupados,
    render_tabela_detalhada
)

# 2. Função main() - SUBSTITUA a linha:
# filtered_df = render_sidebar(df)
# POR:
filtered_df = render_sidebar_accordion(df)

# 3. Aba Visão Geral - SUBSTITUA o bloco de KPIs (col1-col5) por:
render_kpi_row_completa(filtered_df)

# 4. Gráfico Top Logradouros - SUBSTITUA:
# rua_fig = plot_top_ruas(df, 15)
# POR:
rua_fig = plot_top_logradouros_agrupados(filtered_df, 15)

# 5. Tabela Completa - SUBSTITUA a chamada:
# render_table_tab(filtered_df)
# POR:
render_tabela_detalhada(filtered_df)
```

---

## 4. Migração do Banco de Dados

Execute uma vez para criar a nova tabela `catalogo_imoveis`:

```python
# Script standalone: python -c "
from src.etl.sync import CatalogoSync
sync = CatalogoSync()
print('Tabela catalogo_imoveis criada/atualizada')
print('Estatísticas:', sync.obter_estatisticas_catalogo())
"
```

Ou adicione no `load.py` no método `inicializar_banco_historico()`:

```python
# No load.py, dentro de inicializar_banco_historico(), adicione:
from src.etl.sync import CatalogoSync
# O CatalogoSync._init_catalogo_table() já cria a tabela automaticamente
# Basta instanciar uma vez:
CatalogoSync(self.historico_db)
```

---

## 5. Checklist de Validação Pós-Integração

- [ ] Pipeline roda sem erros (`python main.py --force`)
- [ ] Nova tabela `catalogo_imoveis` criada no SQLite
- [ ] Colunas `smart_score` e `classificacao_oportunidade` no Parquet
- [ ] Dashboard carrega com nova sidebar accordion
- [ ] KPI "Oportunidades Gold" aparece na aba Visão Geral
- [ ] Gráfico Top 15 Logradouros mostra ruas agrupadas (sem nº apto)
- [ ] Tabela mostra Smart Score e Classificação
- [ ] Filtros em cascata funcionam nos 3 menus
- [ ] Sincronização marca removidos corretamente (teste: remova alguns IDs do CSV e rode novamente)

---

## 6. Estrutura de Arquivos Final

```
src/
├── etl/
│   ├── sync.py                    # NOVO - Upsert/Sync catálogo
│   ├── smart_score.py             # NOVO - Algoritmo Smart Score
│   ├── pipeline.py                # MODIFICADO - Integra sync + smart_score
│   ├── transform.py               # MODIFICADO - Usa smart_score
│   ├── load.py                    # MODIFICADO - Inicializa catalogo_imoveis
│   ├── schemas.py                 # MODIFICADO - Novos campos
│   └── dashboard/
│       ├── app.py                 # MODIFICADO - Nova UX
│       ├── ux_improvements.py     # NOVO - Componentes UX
│       └── formatters.py          # EXISTENTE - Formatação BRL
└── models/
    └── schemas.py                 # MODIFICADO
```

---

## 7. Rollback Rápido

Se algo der errado, as mudanças são isoladas:

```bash
# Para voltar sidebar antiga:
# Em app.py: filtered_df = render_sidebar(df)  # em vez de render_sidebar_accordion

# Para voltar score antigo:
# Em transform.py: use _calcular_score_oportunidade original
# Comente: from src.etl.smart_score import enriquecer_com_smart_score

# Para desabilitar sync:
# Em pipeline.py: comente bloco sincronizar_catalogo
```

Os módulos novos são **aditivos** - não quebram código existente se não forem importados.