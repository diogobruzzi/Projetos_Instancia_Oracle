"""
Módulo de carga - Salvamento de dados processados em múltiplos formatos.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from src.models.schemas import RelatorioQualidade


class DataLoader:
    """Carregador de dados processados."""

    def __init__(self, config: dict):
        self.config = config
        self.paths = config.get('paths', {})
        self.processed_dir = self.paths.get('processed_dir', 'data/processed')
        self.historico_db = self.paths.get('historico_db', 'data/historico_imoveis.db')

        # Cria diretórios se não existirem
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.historico_db), exist_ok=True)

    def salvar_processado(self, df: pd.DataFrame, snapshot_id: int,
                          metadata: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Salva DataFrame processado em múltiplos formatos.
        Retorna dicionário com caminhos dos arquivos salvos.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"imoveis_rj_snapshot_{snapshot_id}_{timestamp}"

        saved_files = {}

        # 1. Parquet (formato principal - eficiente e preserva tipos)
        parquet_path = os.path.join(self.processed_dir, f"{base_name}.parquet")
        df.to_parquet(parquet_path, index=False, compression='snappy')
        saved_files['parquet'] = parquet_path

        # 2. CSV (para compatibilidade)
        csv_path = os.path.join(self.processed_dir, f"{base_name}.csv")
        df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
        saved_files['csv'] = csv_path

        # 3. JSON (metadados + amostra)
        json_path = os.path.join(self.processed_dir, f"{base_name}_metadata.json")
        meta = {
            'snapshot_id': snapshot_id,
            'timestamp': timestamp,
            'total_registros': len(df),
            'colunas': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'metadata_origem': metadata or {},
            'estatisticas': self._calcular_estatisticas_salvamento(df),
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2, default=str)
        saved_files['metadata_json'] = json_path

        # 4. Atualiza arquivo "latest" (symlink ou cópia para acesso fácil)
        self._atualizar_latest(df, snapshot_id, timestamp)

        return saved_files

    def _calcular_estatisticas_salvamento(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula estatísticas para metadados de salvamento."""
        stats = {
            'total_registros': int(len(df)),
            'municipios_unicos': int(df['cidade_normalizada'].nunique()) if 'cidade_normalizada' in df.columns else 0,
            'bairros_unicos': int(df['bairro_normalizado'].nunique()) if 'bairro_normalizado' in df.columns else 0,
        }

        # Numéricas
        for col in ['preco', 'avaliacao', 'desconto_informado', 'desconto_calculado',
                    'score_oportunidade', 'preco_m2_privativa', 'preco_m2_total', 'preco_m2_terreno']:
            if col in df.columns:
                stats[f'{col}_media'] = float(df[col].mean()) if not df[col].isna().all() else None
                stats[f'{col}_mediana'] = float(df[col].median()) if not df[col].isna().all() else None
                stats[f'{col}_min'] = float(df[col].min()) if not df[col].isna().all() else None
                stats[f'{col}_max'] = float(df[col].max()) if not df[col].isna().all() else None

        # Categóricas
        for col in ['tipo_imovel', 'modalidade_venda', 'faixa_preco', 'faixa_desconto',
                    'cidade_normalizada']:
            if col in df.columns:
                stats[f'{col}_distribuicao'] = df[col].value_counts().head(20).to_dict()

        return stats

    def _atualizar_latest(self, df: pd.DataFrame, snapshot_id: int, timestamp: str):
        """Atualiza arquivos 'latest' para acesso rápido."""
        latest_parquet = os.path.join(self.processed_dir, "imoveis_rj_latest.parquet")
        latest_csv = os.path.join(self.processed_dir, "imoveis_rj_latest.csv")
        latest_meta = os.path.join(self.processed_dir, "imoveis_rj_latest_metadata.json")

        df.to_parquet(latest_parquet, index=False, compression='snappy')
        df.to_csv(latest_csv, index=False, sep=';', encoding='utf-8')

        meta = {
            'snapshot_id': snapshot_id,
            'timestamp': timestamp,
            'total_registros': len(df),
            'atualizado_em': datetime.now().isoformat(),
        }
        with open(latest_meta, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2, default=str)

    def carregar_latest(self) -> Optional[pd.DataFrame]:
        """Carrega a versão mais recente processada."""
        latest_parquet = os.path.join(self.processed_dir, "imoveis_rj_latest.parquet")
        if os.path.exists(latest_parquet):
            return pd.read_parquet(latest_parquet)
        latest_csv = os.path.join(self.processed_dir, "imoveis_rj_latest.csv")
        if os.path.exists(latest_csv):
            return pd.read_csv(latest_csv, sep=';', encoding='utf-8')
        return None

    def carregar_snapshot(self, snapshot_id: int) -> Optional[pd.DataFrame]:
        """Carrega um snapshot específico por ID."""
        # Procura arquivo parquet com o snapshot_id
        for arquivo in os.listdir(self.processed_dir):
            if arquivo.endswith('.parquet') and f'snapshot_{snapshot_id}_' in arquivo:
                caminho = os.path.join(self.processed_dir, arquivo)
                return pd.read_parquet(caminho)
        return None

    def listar_snapshots(self) -> List[Dict[str, Any]]:
        """Lista todos os snapshots disponíveis (exclui arquivos 'latest')."""
        snapshots = []
        for arquivo in os.listdir(self.processed_dir):
            # Ignora arquivos 'latest' que não têm hash completo
            if arquivo.startswith('imoveis_rj_latest_'):
                continue
            if arquivo.endswith('_metadata.json'):
                caminho = os.path.join(self.processed_dir, arquivo)
                try:
                    with open(caminho, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    # Só adiciona se tiver hash válido
                    if meta.get('metadata_origem', {}).get('hash_sha256'):
                        snapshots.append(meta)
                except Exception:
                    pass
        return sorted(snapshots, key=lambda x: x.get('snapshot_id', 0), reverse=True)

    # ===== SQLite Histórico =====
    def inicializar_banco_historico(self):
        """Cria estrutura do banco SQLite histórico."""
        conn = sqlite3.connect(self.historico_db)
        cursor = conn.cursor()

        # Tabela de snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                arquivo_origem TEXT,
                hash_sha256 TEXT,
                total_registros INTEGER,
                registros_validos INTEGER,
                registros_rejeitados INTEGER,
                status_importacao TEXT,
                metadata_json TEXT
            )
        ''')

        # Tabela de imóveis histórico
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imoveis_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                numero_imovel TEXT NOT NULL,
                uf TEXT,
                cidade TEXT,
                cidade_normalizada TEXT,
                bairro TEXT,
                bairro_normalizado TEXT,
                endereco TEXT,
                preco REAL,
                avaliacao REAL,
                desconto_informado REAL,
                desconto_calculado REAL,
                diferenca_desconto REAL,
                financiavel INTEGER,
                modalidade_venda TEXT,
                descricao TEXT,
                link_acesso TEXT,
                tipo_imovel TEXT,
                area_privativa REAL,
                area_total REAL,
                area_terreno REAL,
                quartos INTEGER,
                banheiros INTEGER,
                vagas INTEGER,
                preco_m2_privativa REAL,
                preco_m2_total REAL,
                preco_m2_terreno REAL,
                score_oportunidade REAL,
                faixa_preco TEXT,
                faixa_desconto TEXT,
                data_processamento TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        ''')

        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historico_imovel ON imoveis_historico(numero_imovel)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historico_snapshot ON imoveis_historico(snapshot_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historico_cidade ON imoveis_historico(cidade_normalizada)')

        # Tabela histórico de preços
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_imovel TEXT NOT NULL,
                data_observacao TEXT NOT NULL,
                snapshot_id INTEGER NOT NULL,
                preco_anterior REAL,
                preco_atual REAL,
                diferenca_absoluta REAL,
                variacao_percentual REAL,
                avaliacao_anterior REAL,
                avaliacao_atual REAL,
                desconto_anterior REAL,
                desconto_atual REAL,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_precos_imovel ON historico_precos(numero_imovel)')

        # Tabela histórico de status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_imovel TEXT NOT NULL,
                primeira_identificacao TEXT,
                ultima_identificacao TEXT,
                primeira_ausencia TEXT,
                status_observado TEXT,
                qtd_snapshots_presente INTEGER DEFAULT 0,
                qtd_snapshots_ausente INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_imovel ON historico_status(numero_imovel)')

        conn.commit()
        conn.close()

    def salvar_snapshot_historico(self, df: pd.DataFrame, snapshot_metadata: Dict[str, Any]) -> int:
        """Salva snapshot no banco histórico com detecção de mudanças."""
        self.inicializar_banco_historico()

        conn = sqlite3.connect(self.historico_db)
        cursor = conn.cursor()

        try:
            # Inicia transação
            conn.execute('BEGIN TRANSACTION')

            # 1. Insere snapshot
            cursor.execute('''
                INSERT INTO snapshots (data_hora, arquivo_origem, hash_sha256,
                                       total_registros, registros_validos, registros_rejeitados,
                                       status_importacao, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_metadata.get('data_hora', datetime.now().isoformat()),
                snapshot_metadata.get('arquivo_origem', ''),
                snapshot_metadata.get('hash_sha256', ''),
                snapshot_metadata.get('total_registros', len(df)),
                snapshot_metadata.get('registros_validos', len(df)),
                snapshot_metadata.get('registros_rejeitados', 0),
                snapshot_metadata.get('status_importacao', 'SUCESSO'),
                json.dumps(snapshot_metadata, ensure_ascii=False, default=str)
            ))
            snapshot_id = cursor.lastrowid

            # 2. Prepara dados para imoveis_historico
            colunas_historico = [
                'snapshot_id', 'numero_imovel', 'uf', 'cidade', 'cidade_normalizada',
                'bairro', 'bairro_normalizado', 'endereco', 'preco', 'avaliacao',
                'desconto_informado', 'desconto_calculado', 'diferenca_desconto',
                'financiavel', 'modalidade_venda', 'descricao', 'link_acesso',
                'tipo_imovel', 'area_privativa', 'area_total', 'area_terreno',
                'quartos', 'banheiros', 'vagas', 'preco_m2_privativa',
                'preco_m2_total', 'preco_m2_terreno', 'score_oportunidade',
                'faixa_preco', 'faixa_desconto', 'data_processamento'
            ]

            dados_historico = []
            for _, row in df.iterrows():
                registro = [snapshot_id]
                for col in colunas_historico[1:]:  # pula snapshot_id
                    val = row.get(col)
                    if pd.isna(val):
                        registro.append(None)
                    elif isinstance(val, (np.integer, np.floating)):
                        registro.append(float(val) if isinstance(val, np.floating) else int(val))
                    elif isinstance(val, np.bool_):
                        registro.append(bool(val))
                    else:
                        registro.append(val)
                dados_historico.append(tuple(registro))

            # Insere em lote
            placeholders = ','.join(['?' for _ in colunas_historico])
            cursor.executemany(
                f'INSERT INTO imoveis_historico ({",".join(colunas_historico)}) VALUES ({placeholders})',
                dados_historico
            )

            # 3. Detecta mudanças de preço/desconto (compara com snapshot anterior)
            self._detectar_mudancas(cursor, snapshot_id, df)

            # 4. Atualiza histórico de status
            self._atualizar_historico_status(cursor, snapshot_id, df)

            conn.commit()
            return snapshot_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _detectar_mudancas(self, cursor: sqlite3.Cursor, snapshot_id: int, df_atual: pd.DataFrame):
        """Detecta e registra mudanças de preço e desconto."""
        # Busca snapshot anterior
        cursor.execute('''
            SELECT MAX(id) FROM snapshots WHERE id < ?
        ''', (snapshot_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return  # Primeiro snapshot

        snapshot_anterior_id = row[0]

        # Busca dados do snapshot anterior
        cursor.execute('''
            SELECT numero_imovel, preco, avaliacao, desconto_informado
            FROM imoveis_historico WHERE snapshot_id = ?
        ''', (snapshot_anterior_id,))
        dados_anteriores = {r[0]: r[1:] for r in cursor.fetchall()}

        # Compara com dados atuais
        mudancas_preco = []
        for _, row in df_atual.iterrows():
            num = row['numero_imovel']
            if num in dados_anteriores:
                preco_ant, aval_ant, desc_ant = dados_anteriores[num]
                preco_atual = row['preco']
                aval_atual = row['avaliacao']
                desc_atual = row['desconto_informado']

                # Só registra se houve mudança significativa
                if (preco_ant and preco_atual and preco_ant != preco_atual) or \
                   (aval_ant and aval_atual and aval_ant != aval_atual) or \
                   (desc_ant is not None and desc_atual is not None and abs(desc_ant - desc_atual) > 0.01):

                    diff_abs = preco_atual - preco_ant if preco_ant and preco_atual else 0
                    var_pct = (diff_abs / preco_ant * 100) if preco_ant and preco_ant > 0 else 0

                    mudancas_preco.append((
                        num, datetime.now().isoformat(), snapshot_id,
                        preco_ant, preco_atual, diff_abs, var_pct,
                        aval_ant, aval_atual, desc_ant, desc_atual
                    ))

        if mudancas_preco:
            cursor.executemany('''
                INSERT INTO historico_precos
                (numero_imovel, data_observacao, snapshot_id,
                 preco_anterior, preco_atual, diferenca_absoluta, variacao_percentual,
                 avaliacao_anterior, avaliacao_atual, desconto_anterior, desconto_atual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', mudancas_preco)

    def _atualizar_historico_status(self, cursor: sqlite3.Cursor, snapshot_id: int, df_atual: pd.DataFrame):
        """Atualiza histórico de status dos imóveis (novo, ativo, ausente, reapareceu)."""
        # Busca status anterior
        cursor.execute('SELECT numero_imovel, status_observado, qtd_snapshots_presente, qtd_snapshots_ausente, primeira_identificacao, ultima_identificacao, primeira_ausencia FROM historico_status')
        status_anterior = {r[0]: r[1:] for r in cursor.fetchall()}

        imoveis_atuais = set(df_atual['numero_imovel'].tolist())
        imoveis_anteriores = set(status_anterior.keys())
        agora = datetime.now().isoformat()

        # Imóveis atuais
        for num in imoveis_atuais:
            if num in status_anterior:
                status_ant, qtd_pres, qtd_aus, prim_id, ult_id, prim_aus = status_anterior[num]
                if status_ant in ['Ausente', 'Reapareceu']:
                    # Reapareceu
                    cursor.execute('''
                        UPDATE historico_status
                        SET status_observado = 'Reapareceu',
                            qtd_snapshots_presente = qtd_snapshots_presente + 1,
                            ultima_identificacao = ?
                        WHERE numero_imovel = ?
                    ''', (agora, num))
                else:
                    # Continua ativo
                    cursor.execute('''
                        UPDATE historico_status
                        SET status_observado = 'Ativo',
                            qtd_snapshots_presente = qtd_snapshots_presente + 1,
                            ultima_identificacao = ?
                        WHERE numero_imovel = ?
                    ''', (agora, num))
            else:
                # Novo imóvel
                cursor.execute('''
                    INSERT INTO historico_status
                    (numero_imovel, primeira_identificacao, ultima_identificacao,
                     status_observado, qtd_snapshots_presente, qtd_snapshots_ausente)
                    VALUES (?, ?, ?, 'Novo', 1, 0)
                ''', (num, agora, agora))

        # Imóveis ausentes (estavam antes, não estão agora)
        for num in imoveis_anteriores - imoveis_atuais:
            status_ant, qtd_pres, qtd_aus, prim_id, ult_id, prim_aus = status_anterior[num]
            if status_ant != 'Ausente':
                cursor.execute('''
                    UPDATE historico_status
                    SET status_observado = 'Ausente',
                        qtd_snapshots_ausente = qtd_snapshots_ausente + 1,
                        primeira_ausencia = ?
                    WHERE numero_imovel = ?
                ''', (agora, num))
            else:
                cursor.execute('''
                    UPDATE historico_status
                    SET qtd_snapshots_ausente = qtd_snapshots_ausente + 1
                    WHERE numero_imovel = ?
                ''', (num,))

    def salvar_relatorio_qualidade(self, relatorio: RelatorioQualidade, snapshot_id: int) -> str:
        """Salva relatório de qualidade em JSON."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.processed_dir, f"qualidade_snapshot_{snapshot_id}_{timestamp}.json")

        data = {
            'snapshot_id': snapshot_id,
            'timestamp': timestamp,
            'resumo': {
                'total_registros': relatorio.total_registros,
                'registros_validos': relatorio.registros_validos,
                'registros_rejeitados': relatorio.registros_rejeitados,
                'registros_com_avisos': relatorio.registros_com_avisos,
            },
            'erros_por_tipo': relatorio.erros_por_tipo,
            'avisos_por_tipo': relatorio.avisos_por_tipo,
            'detalhes': [
                {
                    'numero_imovel': r.numero_imovel,
                    'valido': r.valido,
                    'erros': r.erros,
                    'avisos': r.avisos,
                }
                for r in relatorio.detalhes
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return filepath


def salvar_dados_processados(df: pd.DataFrame, config: dict, snapshot_id: int,
                             metadata: Dict = None) -> Dict[str, str]:
    """Função de conveniência para salvamento rápido."""
    loader = DataLoader(config)
    return loader.salvar_processado(df, snapshot_id, metadata)