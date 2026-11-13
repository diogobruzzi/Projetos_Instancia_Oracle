# Radar Imobiliário RJ - Documentação do Projeto

## Visão Geral

Plataforma de inteligência imobiliária para processamento, análise e monitoramento de imóveis da Caixa Econômica Federal no estado do Rio de Janeiro. O sistema automatiza o pipeline ETL completo: extração de CSV bruto, transformação e enriquecimento, validação de qualidade, carga em múltiplos formatos e rastreamento histórico em SQLite.

---

## Arquitetura

```
radar_imobiliario_rj/
├── config/
│   └── settings.yaml          # Configuração central (paths, CSV, validação, enriquecimento, logging)
├── data/
│   ├── raw/                   # CSV original da Caixa
│   ├── processed/             # Parquet, CSV, JSON processados + metadata
│   └── historico_imoveis.db   # Banco SQLite histórico
├── logs/
│   └── pipeline.log           # Logs de execução
├── src/
│   ├── models/
│   │   └── schemas.py         # Dataclasses, Enums, validação
│   └── etl/
│       ├── extract.py         # CSVExtractor - leitura + hash SHA-256
│       ├── transform.py       # DataTransformer - limpeza, features, score
│       ├── validate.py        # DataValidator - regras de qualidade
│       ├── load.py            # DataLoader - multi-formato + SQLite histórico
│       └── pipeline.py        # ETLPipeline - orquestração 5 etapas
└── main.py                    # CLI entry point
```

---

## Pipeline ETL - 5 Etapas

### 1. Extração (`extract.py`)
- Lê CSV da Caixa (latin-1, delimitador `;`, 2 linhas de cabeçalho)
- Calcula **SHA-256** do arquivo para detecção de mudanças
- Retorna DataFrame bruto + metadados (tamanho, hash, timestamp, encoding)

### 2. Transformação (`transform.py`)
**Conversões:**
- `br_price_to_float()`: "1.234,56" → 1234.56
- `br_discount_to_float()`: "60.39" → 60.39
- `normalizar_texto()`: remove acentos, uppercase, trim

**Extração de features da descrição (regex):**
| Feature | Padrão |
|---------|--------|
| `tipo_imovel` | apartamento / casa / terreno / sala comercial |
| `area_privativa` | `(\d+[.,]\d+)\s*de\s*área\s*privativa` |
| `area_total` | `(\d+[.,]\d+)\s*de\s*área\s*total` |
| `area_terreno` | `(\d+[.,]\d+)\s*de\s*área\s*do\s*terreno` |
| `quartos` | `(\d+)\s*qto` |
| `banheiros` | contagem de `WC` ou `lavabo` |
| `vagas` | `(\d+)\s*vaga` |

**Métricas derivadas:**
- `preco_m2_privativa`, `preco_m2_total`, `preco_m2_terreno`
- `faixa_preco`: 9 categorias (Até 50k → 5M+)
- `faixa_desconto`: 10 categorias (0-10% → 90-100%)
- `score_oportunidade` (0-100) - ver seção abaixo

### 3. Validação (`validate.py`)
**Erros (rejeita registro):**
- Número do imóvel ausente
- Preço/Avaliação/Desconto ausentes ou inválidos
- Desconto negativo ou > 100%

**Avisos (registra mas não rejeita):**
- Preço muito baixo/alto (config: 1k - 50M)
- Avaliação muito baixa/alta
- Desconto muito alto
- Preço > Avaliação (desconto negativo implícito)
- Desconto informado vs calculado divergente (> 5%)
- Tipo de imóvel não identificado
- Áreas/quartos/banheiros/vagas faltantes
- Link de acesso inválido
- UF diferente de RJ

**Resultado:** `RelatorioQualidade` com contadores e detalhes por registro.

### 4. Carga - Arquivos Processados (`load.py::salvar_processado`)
Gera 4 artefatos por snapshot:
| Formato | Arquivo | Uso |
|---------|---------|-----|
| Parquet | `imoveis_rj_snapshot_{id}_{timestamp}.parquet` | Principal (tipos preservados, compressão snappy) |
| CSV | `imoveis_rj_snapshot_{id}_{timestamp}.csv` | Compatibilidade (utf-8, `;`) |
| JSON | `imoveis_rj_snapshot_{id}_{timestamp}_metadata.json` | Metadados + estatísticas |
| Latest | `imoveis_rj_latest.*` | Acesso rápido ao último snapshot |

### 5. Carga - Banco Histórico (`load.py::salvar_snapshot_historico`)
**Tabelas:**

```sql
-- Snapshots executados
snapshots (id, data_hora, arquivo_origem, hash_sha256, total_registros,
           registros_validos, registros_rejeitados, status_importacao, metadata_json)

-- Todos os imóveis de todos os snapshots
imoveis_historico (id, snapshot_id, numero_imovel, uf, cidade, cidade_normalizada,
                   bairro, bairro_normalizado, endereco, preco, avaliacao,
                   desconto_informado, desconto_calculado, diferenca_desconto,
                   financiavel, modalidade_venda, descricao, link_acesso,
                   tipo_imovel, area_privativa, area_total, area_terreno,
                   quartos, banheiros, vagas, preco_m2_privativa,
                   preco_m2_total, preco_m2_terreno, score_oportunidade,
                   faixa_preco, faixa_desconto, data_processamento)

-- Variações de preço/desconto entre snapshots consecutivos
historico_precos (id, numero_imovel, data_observacao, snapshot_id,
                  preco_anterior, preco_atual, diferenca_absoluta, variacao_percentual,
                  avaliacao_anterior, avaliacao_atual, desconto_anterior, desconto_atual)

-- Status de presença do imóvel ao longo do tempo
historico_status (id, numero_imovel, primeira_identificacao, ultima_identificacao,
                  primeira_ausencia, status_observado, qtd_snapshots_presente,
                  qtd_snapshots_ausente)
```

**Estados de status:**
- `Novo` - apareceu pela primeira vez
- `Ativo` - presente no snapshot atual
- `Ausente` - estava no anterior, sumiu no atual
- `Reapareceu` - estava ausente, voltou a aparecer

**Índices criados:**
- `idx_historico_imovel` (numero_imovel)
- `idx_historico_snapshot` (snapshot_id)
- `idx_historico_cidade` (cidade_normalizada)
- `idx_precos_imovel` (numero_imovel)
- `idx_status_imovel` (numero_imovel)

---

## Score de Oportunidade (0-100)

```python
def _calcular_score_oportunidade(imovel):
    score = 0
    
    # 1. Desconto percentual (0-30 pts)
    # 70%+ = 30, 60%+ = 25, 50%+ = 20, 40%+ = 15, 30%+ = 10, 20%+ = 5, else = desconto/2
    
    # 2. Diferença absoluta avaliação - preço (0-20 pts)
    # >=200k = 20, >=100k = 15, >=50k = 10, >=20k = 5
    
    # 3. Preço relativo à mediana municipal (0-20 pts) - placeholder 10
    
    # 4. Financiável (0-10 pts) - sim = 10
    
    # 5. Tipo de imóvel (0-10 pts)
    # Apartamento = 10, Casa = 8, Terreno = 5
    
    # 6. Qualidade dos dados (0-10 pts)
    # area_privativa = 3, quartos = 2, banheiros = 2, vagas = 2, descricao>50 = 1
    
    return round(min(100, max(0, score)), 1)
```

---

## Configuração (`config/settings.yaml`)

```yaml
paths:
  raw_data: data/raw/Lista_imoveis_RJ.csv
  processed_dir: data/processed
  historico_db: data/historico_imoveis.db

csv:
  encoding: latin-1
  delimiter: ';'
  skip_rows: 2

validation:
  price_min: 1000
  price_max: 50000000
  evaluation_min: 1000
  evaluation_max: 50000000
  discount_min: 0
  discount_max: 100
  max_price_vs_evaluation_ratio: 2.0
  max_discount_diff_pct: 5.0

enrichment:
  extract_area_privativa: true
  extract_area_total: true
  extract_area_terreno: true
  extract_quartos: true
  extract_banheiros: true
  extract_vagas: true
  extract_tipo_imovel: true
  calculate_price_per_m2: true
  calculate_discount_calculated: true
  calculate_score_oportunidade: true

logging:
  level: INFO
  file: logs/pipeline.log
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

---

## Como Executar

### Pipeline completo (força execução mesmo se arquivo não mudou)
```bash
python3 main.py --force
```

### Pipeline com verificação de mudança (pula se hash idêntico)
```bash
python3 main.py
```

### Com estatísticas detalhadas
```bash
python3 main.py --force --stats
```

### Com relatório de qualidade
```bash
python3 main.py --force --quality
```

### Iniciar dashboard Streamlit (futuro)
```bash
python3 main.py --dashboard
```

### Saída típica (execução completa):
```
============================================================
RADAR IMOBILIÁRIO RJ - PIPELINE ETL
============================================================

✅ PIPELINE EXECUTADO COM SUCESSO
   Snapshot ID: 6
   Registros processados: 8,323
   Registros válidos: 8,323
   Registros rejeitados: 0
   Tempo: 5.0s

📊 ESTATÍSTICAS:
   total_registros: 8323
   municipios_unicos: 47
   bairros_unicos: 716
   tipos_imovel:
     Apartamento: 5881
     Casa: 2191
     Terreno/Lote: 251
   modalidades:
     Venda Direta Online: 5358
     Venda Online: 1543
     Leilão SFI - Edital Único: 1004
     Licitação Aberta: 418
   financiaveis_pct: 6.91
   preco:
     media: 113661.23
     mediana: 87775.99
     min: 11300.0
     max: 9303775.03
   desconto:
     media: 42.35%
     mediana: 43.37%
   score_oportunidade:
     media: 52.18
     mediana: 53.0
```

### Saída típica (skip - arquivo não alterado):
```
============================================================
RADAR IMOBILIÁRIO RJ - PIPELINE ETL
============================================================

✅ PIPELINE EXECUTADO COM SUCESSO
   Snapshot ID: 6
   Registros processados: 8,323
   Carregado último snapshot (arquivo não alterado)
```

---

## Modelos de Dados (`src/models/schemas.py`)

### Enums
```python
class TipoImovel(Enum):
    APARTAMENTO = "Apartamento"
    CASA = "Casa"
    TERRENO_LOTE = "Terreno/Lote"
    SALA_COMERCIAL = "Sala Comercial"
    NAO_IDENTIFICADO = "Não Identificado"

class ModalidadeVenda(Enum):
    VENDA_DIRETA = "Venda Direta"
    VENDA_ONLINE = "Venda Online"
    LEILAO = "Leilão"
    LICITACAO = "Licitação"
    OUTRA = "Outra"

class StatusHistorico(Enum):
    NOVO = "Novo"
    ATIVO = "Ativo"
    AUSENTE = "Ausente"
    REAPARECEU = "Reapareceu"
```

### Dataclasses Principais
- `ImovelRaw` - dados brutos do CSV (strings originais)
- `ImovelProcessado` - dados enriquecidos + métricas derivadas
- `ValidacaoResultado` - resultado por registro (valido, erros[], avisos[])
- `RelatorioQualidade` - agregado (total, validos, rejeitados, com_avisos, erros_por_tipo, avisos_por_tipo, detalhes[])
- `COLUNAS_PROCESSADO` - lista ordenada de 41 colunas do DataFrame final

---

## Detecção de Mudanças

O pipeline **só executa** se o arquivo CSV tiver mudado (hash SHA-256 diferente do último snapshot processado).

```python
# extract.py
def verificar_mudanca(self, hash_anterior: Optional[str]) -> bool:
    if hash_anterior is None:
        return True  # primeira execução
    hash_atual = self._calcular_hash()  # lê só bytes do arquivo
    return hash_atual != hash_anterior

# pipeline.py
def _obter_ultimo_hash(self) -> Optional[str]:
    snapshots = self.loader.listar_snapshots()  # ignora arquivos 'latest_*'
    if snapshots:
        return snapshots[0].get('metadata_origem', {}).get('hash_sha256')
    return None
```

---

## Exemplos de Consultas SQLite

### Últimos 5 snapshots
```sql
SELECT id, data_hora, total_registros, registros_validos 
FROM snapshots 
ORDER BY id DESC LIMIT 5;
```

### Imóveis com maior desconto no último snapshot
```sql
SELECT numero_imovel, cidade_normalizada, bairro_normalizado, 
       preco, avaliacao, desconto_informado, score_oportunidade
FROM imoveis_historico
WHERE snapshot_id = (SELECT MAX(id) FROM snapshots)
ORDER BY desconto_informado DESC LIMIT 20;
```

### Variação de preço de um imóvel específico
```sql
SELECT data_observacao, preco_anterior, preco_atual, variacao_percentual
FROM historico_precos
WHERE numero_imovel = '8787716155447'
ORDER BY data_observacao;
```

### Imóveis que reapareceram
```sql
SELECT numero_imovel, primeira_identificacao, ultima_identificacao, 
       qtd_snapshots_presente, qtd_snapshots_ausente
FROM historico_status
WHERE status_observado = 'Reapareceu';
```

### Top 10 municípios por quantidade de imóveis
```sql
SELECT cidade_normalizada, COUNT(*) as qtd
FROM imoveis_historico
WHERE snapshot_id = (SELECT MAX(id) FROM snapshots)
GROUP BY cidade_normalizada
ORDER BY qtd DESC LIMIT 10;
```

---

## Dependências

```bash
pip install pandas pyarrow pyyaml requests
```

- `pandas` - manipulação de dados
- `pyarrow` - escrita Parquet
- `pyyaml` - configuração YAML
- `requests` - download HTTP (script inicial)

---

## Logs

Arquivo: `logs/pipeline.log`
- Nível: INFO (configurável)
- Formato: timestamp - módulo - nível - mensagem
- Rotação: manual (arquivo único, append)

---

## Próximas Fases (Roadmap)

| Fase | Descrição | Status |
|------|-----------|--------|
| 1 | Diagnóstico & Download | ✅ Concluído |
| 2 | Modelagem & Tratamento (ETL) | ✅ Concluído |
| 3 | Histórico SQLite | ✅ Implementado |
| 4 | Dashboard Executive | ✅ Concluído |
| 5 | Mapa Interativo RJ + Drill-down | ✅ Concluído |
| 6 | Inteligência & Simulador | ⏳ Planejada |
| 7 | Alertas & Evolução | ⏳ Planejada |
| 8 | Validação Final | ⏳ Planejada |

---

## Dashboard Executive (Fase 4) - `src/etl/dashboard/app.py`

### Funcionalidades
- **3 Abas principais:** Visão Geral, Mapa RJ + Drill-down, Tabela Completa
- **Sidebar com filtros cascata:** Município → Bairro (depende do município) → Tipo → Modalidade → Faixa Preço → Faixa Desconto → Financiável → Score Mínimo → Range Preço
- **5 KPIs no topo:** Total Imóveis, Preço Médio, Desconto Médio, Score Médio, % Financiáveis
- **3 Gráficos Plotly interativos na Visão Geral (mantidos):**
  - Distribuição por Tipo (bar)
  - Distribuição por Modalidade (bar)
  - Top 15 Municípios (horizontal bar)
- **Gráficos removidos (conforme solicitação):** Score histograma+boxplot, Preço histograma, Desconto histograma, Boxplot Preço/Tipo, Scatter Preço vs Desconto, Faixa Preço/Desconto, Evolução Snapshots, Status donut, Resumo Snapshots

### Mapa Interativo RJ + Drill-down Hierárquico
- **Mapa scatter_mapbox** do Rio de Janeiro com 92+ municípios mapeados
  - Tamanho do círculo = quantidade de imóveis (escala √n)
  - Cor = desconto médio (%) - escala RdYlGn (vermelho=baixo, verde=alto)
  - Hover com: quantidade, preço médio/mediano, desconto médio, score médio
- **Drill-down 4 níveis:** Estado → Município → Bairro → Logradouro
  - Nível 1: Tabela de municípios com Qtd, Preço Médio/Mediana, Desconto Médio, Score Médio, % Financiáveis
  - Nível 2: Bairros do município selecionado (mesmas métricas)
  - Nível 3: Logradouros do bairro selecionado + detalhe dos imóveis na rua

### Tabela Completa
- Paginação configurável (25/50/100/200)
- Exportação CSV (sep=;, utf-8)
- 17 colunas principais com formatação monetária e percentual

### Como Executar
```bash
# Via CLI (porta configurável)
python3 main.py --dashboard --port 8501

# Ou diretamente
streamlit run src/etl/dashboard/app.py --server.port=8501
```
Acesse: http://localhost:8501

### Dependências Adicionais
```bash
pip install streamlit>=1.28.0 plotly>=5.17.0
```

---

## Métricas Atuais (Última Execução)

- **Registros processados:** 8.323
- **Municípios únicos:** 47
- **Bairros únicos:** 716
- **Tipos:** Apartamento (5.881), Casa (2.191), Terreno/Lote (251)
- **Modalidades:** Venda Direta Online (5.358), Venda Online (1.543), Leilão (1.004), Licitação (418)
- **Financiáveis:** 6,9%
- **Preço médio:** R$ 113.661 | Mediana: R$ 87.776
- **Desconto médio:** 42,35% | Mediana: 43,37%
- **Score oportunidade médio:** 52,2 | Mediana: 53,0
- **Avisos de qualidade:** 1.939 (principalmente áreas/quartos/banheiros/vagas faltantes)
- **Erros:** 0
- **Snapshots no histórico:** 14
- **Registros históricos (imoveis_historico):** 116.522
- **Registros de status (historico_status):** 8.323 (todos "Ativo")
- **Registros histórico:** 8.323 × 14 snapshots
- **Tempo execução:** ~5 segundos

---

## Tamanho do Projeto

### Código Fonte (Python)
| Módulo | Arquivo | Linhas | Descrição |
|--------|---------|--------|-----------|
| CLI | `main.py` | 111 | Entry point, argparse, output formatting, dashboard port |
| Config | `config/settings.yaml` | 61 | YAML config paths, CSV, validation, enrichment, logging, geo, dashboard |
| Schemas | `src/models/schemas.py` | 226 | Dataclasses, Enums, validação, COLUNAS_PROCESSADO (31 cols) |
| Extract | `src/etl/extract.py` | 80 | CSVExtractor, SHA-256 hash, change detection |
| Transform | `src/etl/transform.py` | 364 | DataTransformer, BR parsing, regex features, score 0-100 |
| Validate | `src/etl/validate.py` | 200 | DataValidator, erro/aviso rules, estatísticas |
| Load | `src/etl/load.py` | 478 | DataLoader, multi-formato, SQLite 4 tabelas, histórico |
| Pipeline | `src/etl/pipeline.py` | 271 | ETLPipeline, 5 etapas, logging, snapshot management |
| Dashboard | `src/etl/dashboard/app.py` | 772 | Streamlit, mapa RJ, drill-down, filtros cascata, Plotly |
| **Total Python** | **9 arquivos** | **~2.563 linhas** | **~85 KB código** |

### Dados
| Item | Tamanho | Formato |
|------|---------|---------|
| CSV Bruto (Caixa) | 2,83 MB | latin-1, `;`, 2 header rows |
| Parquet Processado | ~3,2 MB | snappy compression |
| CSV Processado | ~4,1 MB | utf-8, `;` |
| JSON Metadata | ~15 KB | utf-8, indent=2 |
| SQLite Histórico | ~18 MB | 4 tabelas, 5 índices |
| Logs | ~50 KB | texto, append |

### Estrutura de Diretórios
```
radar_imobiliario_rj/
├── config/settings.yaml              (45 linhas)
├── data/
│   ├── raw/Lista_imoveis_RJ.csv      (2.8 MB, 8.323 linhas)
│   ├── processed/                    (6 arquivos × snapshot)
│   │   ├── imoveis_rj_snapshot_*.parquet
│   │   ├── imoveis_rj_snapshot_*.csv
│   │   ├── imoveis_rj_snapshot_*_metadata.json
│   │   └── imoveis_rj_latest.* (3 arquivos)
│   └── historico_imoveis.db          (18 MB, 116.522 registros)
├── logs/pipeline.log                 (~50 KB)
├── src/
│   ├── models/schemas.py             (180 linhas)
│   └── etl/
│       ├── extract.py                (80 linhas)
│       ├── transform.py              (360 linhas)
│       ├── validate.py               (200 linhas)
│       ├── load.py                   (475 linhas)
│       └── pipeline.py               (270 linhas)
├── main.py                           (100 linhas)
└── PROJECT.md                        (este arquivo)
```

### Dependências (requirements.txt)
```
pandas>=2.0.0
pyarrow>=12.0.0
pyyaml>=6.0
requests>=2.31.0
streamlit>=1.28.0    # Dashboard
plotly>=5.17.0       # Gráficos interativos
```

### Complexidade Ciclomática (estimada)
- **Baixa:** extract.py, schemas.py, main.py
- **Média:** validate.py, pipeline.py
- **Alta:** transform.py (regex features, score), load.py (SQLite transações, batch inserts)

### Cobertura Funcional
| Funcionalidade | Status | Arquivo Principal |
|----------------|--------|-------------------|
| Download CSV | ✅ | download_caixa_imoveis.py (raiz) |
| Extração CSV | ✅ | extract.py |
| Hash SHA-256 change detection | ✅ | extract.py + pipeline.py |
| Parsing BR (preço/desconto) | ✅ | transform.py |
| Normalização texto/geo | ✅ | transform.py |
| Regex feature extraction | ✅ | transform.py |
| Price/m² calculation | ✅ | transform.py |
| Score oportunidade 0-100 | ✅ | transform.py |
| Validação erro/aviso | ✅ | validate.py |
| Relatório qualidade | ✅ | validate.py + load.py |
| Multi-formato output | ✅ | load.py |
| SQLite histórico 4 tabelas | ✅ | load.py |
| Detecção mudanças preço/desc | ✅ | load.py::_detectar_mudancas |
| Status tracking (Novo/Ativo/Ausente/Reapareceu) | ✅ | load.py::_atualizar_historico_status |
| CLI com flags | ✅ | main.py |
| Dashboard Streamlit | 🔄 | src/etl/dashboard/app.py |

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError: pandas` | `pip install pandas pyarrow pyyaml requests --break-system-packages` |
| `externally-managed-environment` | Use `--break-system-packages` ou crie venv |
| Pipeline pula execução | Arquivo não mudou. Use `--force` para forçar |
| Encoding error no CSV | Verifique `encoding: latin-1` no settings.yaml |
| SQLite locked | Feche outras conexões; o pipeline usa transações curtas |
| Memória alta no Parquet | PyArrow usa streaming; 8k registros ≈ 10MB |

---

## Licença

Projeto interno - Radar Imobiliário RJ
Desenvolvido com Python 3.11+, Pandas, SQLite, Playwright (download inicial)