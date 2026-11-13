"""
Módulo de Sincronização (Upsert) - Radar Imobiliário RJ
Implementa lógica de upsert limpa para sincronização do catálogo da Caixa.
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path


class CatalogoSync:
    """
    Gerenciador de sincronização do catálogo de imóveis.

    Lógica de Upsert:
    - PK: id_imovel (numero_imovel)
    - Se existe: ATUALIZA preco, avaliacao, desconto_informado, data_ultima_atualizacao
    - Se novo: INSERE com data_primeira_aparicao
    - Se ausente na raspagem atual: ativo = FALSE, status = 'Removido/Arrematado'
    """

    def __init__(self, db_path: str = 'data/historico_imoveis.db'):
        self.db_path = db_path
        self._init_catalogo_table()

    def _init_catalogo_table(self):
        """Cria/atualiza tabela de catálogo ativo com campos necessários para sync."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela principal do catálogo (estado atual dos imóveis)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS catalogo_imoveis (
                id_imovel TEXT PRIMARY KEY,
                uf TEXT,
                cidade TEXT,
                cidade_normalizada TEXT,
                bairro TEXT,
                bairro_normalizado TEXT,
                endereco TEXT,
                endereco_limpo TEXT,  -- Rua/Condomínio sem números de apto/bloco
                preco REAL,
                avaliacao REAL,
                desconto_informado REAL,
                desconto_calculado REAL,
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
                smart_score REAL,
                faixa_preco TEXT,
                faixa_desconto TEXT,
                ativo INTEGER DEFAULT 1,
                status TEXT DEFAULT 'Ativo',
                data_primeira_aparicao TEXT,
                data_ultima_atualizacao TEXT,
                data_remocao TEXT,
                snapshot_id_origem INTEGER,
                snapshot_id_atualizacao INTEGER
            )
        ''')

        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_cidade ON catalogo_imoveis(cidade_normalizada)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_bairro ON catalogo_imoveis(bairro_normalizado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_ativo ON catalogo_imoveis(ativo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_status ON catalogo_imoveis(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_score ON catalogo_imoveis(smart_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_catalogo_endereco_limpo ON catalogo_imoveis(endereco_limpo)')

        conn.commit()
        conn.close()

    @staticmethod
    def _limpar_endereco(endereco: str) -> str:
        """
        Limpa endereço para agrupar por nome da rua/condomínio.
        Remove números de apartamento, blocos, complementos.
        """
        if not endereco or pd.isna(endereco):
            return ''

        import re
        endereco = str(endereco).upper().strip()

        # Remove padrões de apartamento/casa/lote/bloco
        padroes_remover = [
            r'\s*,?\s*(AP|APTO|APARTAMENTO)\.?\s*\d+[A-Z]?',  # AP 101, APTO 202
            r'\s*,?\s*(CASA|CS)\.?\s*\d+[A-Z]?',               # CASA 01, CS 02
            r'\s*,?\s*(BLOCO|BL)\.?\s*[A-Z0-9]+',              # BLOCO A, BL 1
            r'\s*,?\s*(LOTE|LT)\.?\s*\d+',                     # LOTE 10, LT 510
            r'\s*,?\s*(QUADRA|QD)\.?\s*\d+',                   # QUADRA 34, QD 34
            r'\s*,?\s*(SALA|SL)\.?\s*\d+[A-Z]?',               # SALA 101
            r'\s*,?\s*(COBERTURA|COB)\.?\s*\d*',               # COBERTURA
            r'\s*,?\s*N[º°\.]\s*\d+[A-Z]?',                    # N. 106, Nº 201
            r'\s*,?\s*NUMERO\s+\d+[A-Z]?',                     # NUMERO 106
            r'\s*,?\s*ANDAR\s+\d+[A-Z]?',                      # ANDAR 5
        ]

        for padrao in padroes_remover:
            endereco = re.sub(padrao, '', endereco, flags=re.IGNORECASE)

        # Remove números isolados no final (ex: "RUA EXEMPLO 123" -> "RUA EXEMPLO")
        endereco = re.sub(r'\s+\d+[A-Z]?$', '', endereco)

        # Limpa espaços múltiplos e vírgulas órfãs
        endereco = re.sub(r'\s+', ' ', endereco)
        endereco = re.sub(r',\s*,', ',', endereco)
        endereco = endereco.strip(' ,')

        return endereco.strip()

    def sincronizar(self, df_novo: pd.DataFrame, snapshot_id: int) -> Dict[str, int]:
        """
        Executa sincronização completa (Upsert + Marcar ausentes).

        Args:
            df_novo: DataFrame processado com dados da raspagem atual
            snapshot_id: ID do snapshot atual

        Returns:
            Dict com contadores: {'inseridos': X, 'atualizados': Y, 'removidos': Z, 'inalterados': W}
        """
        # Prepara dados: adiciona endereco_limpo
        df = df_novo.copy()
        df['endereco_limpo'] = df['endereco'].apply(self._limpar_endereco)
        df['data_processamento'] = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            conn.execute('BEGIN TRANSACTION')

            agora = datetime.now().isoformat()
            imoveis_atuais = set(df['numero_imovel'].tolist())

            # 1. Busca estado atual do catálogo
            cursor.execute('SELECT id_imovel FROM catalogo_imoveis WHERE ativo = 1')
            imoveis_banco = {r[0] for r in cursor.fetchall()}

            # 2. Identifica novos, existentes e removidos
            novos = imoveis_atuais - imoveis_banco
            existentes = imoveis_atuais & imoveis_banco
            removidos = imoveis_banco - imoveis_atuais

            contadores = {
                'inseridos': 0,
                'atualizados': 0,
                'removidos': 0,
                'inalterados': 0
            }

            # 3. INSERE novos imóveis
            if novos:
                df_novos = df[df['numero_imovel'].isin(novos)]
                colunas = [
                    'id_imovel', 'uf', 'cidade', 'cidade_normalizada', 'bairro', 'bairro_normalizado',
                    'endereco', 'endereco_limpo', 'preco', 'avaliacao', 'desconto_informado',
                    'desconto_calculado', 'financiavel', 'modalidade_venda', 'descricao',
                    'link_acesso', 'tipo_imovel', 'area_privativa', 'area_total', 'area_terreno',
                    'quartos', 'banheiros', 'vagas', 'preco_m2_privativa', 'preco_m2_total',
                    'preco_m2_terreno', 'smart_score', 'faixa_preco', 'faixa_desconto',
                    'ativo', 'status', 'data_primeira_aparicao', 'data_ultima_atualizacao',
                    'data_remocao', 'snapshot_id_origem', 'snapshot_id_atualizacao'
                ]

                dados_novos = []
                for _, row in df_novos.iterrows():
                    reg = (
                        row['numero_imovel'], row['uf'], row['cidade'], row['cidade_normalizada'],
                        row['bairro'], row['bairro_normalizado'], row['endereco'],
                        row['endereco_limpo'], row['preco'], row['avaliacao'],
                        row['desconto_informado'], row['desconto_calculado'],
                        int(row['financiavel']) if not pd.isna(row['financiavel']) else 0,
                        row['modalidade_venda'], row['descricao'], row['link_acesso'],
                        row['tipo_imovel'], row.get('area_privativa'), row.get('area_total'),
                        row.get('area_terreno'), row.get('quartos'), row.get('banheiros'),
                        row.get('vagas'), row.get('preco_m2_privativa'), row.get('preco_m2_total'),
                        row.get('preco_m2_terreno'), row.get('smart_score'),
                        row.get('faixa_preco'), row.get('faixa_desconto'),
                        1, 'Ativo', agora, agora, None, snapshot_id, snapshot_id
                    )
                    dados_novos.append(reg)

                placeholders = ','.join(['?' for _ in colunas])
                cursor.executemany(
                    f'INSERT INTO catalogo_imoveis ({",".join(colunas)}) VALUES ({placeholders})',
                    dados_novos
                )
                contadores['inseridos'] = len(dados_novos)

            # 4. ATUALIZA imóveis existentes (compara valores para evitar updates desnecessários)
            if existentes:
                df_existentes = df[df['numero_imovel'].isin(existentes)]

                for _, row in df_existentes.iterrows():
                    # Verifica se houve mudança real
                    cursor.execute('''
                        SELECT preco, avaliacao, desconto_informado FROM catalogo_imoveis
                        WHERE id_imovel = ?
                    ''', (row['numero_imovel'],))
                    atual = cursor.fetchone()

                    if atual:
                        preco_ant, aval_ant, desc_ant = atual
                        preco_novo = row['preco']
                        aval_novo = row['avaliacao']
                        desc_novo = row['desconto_informado']

                        mudou = (
                            (preco_ant != preco_novo) or
                            (aval_ant != aval_novo) or
                            (abs((desc_ant or 0) - (desc_novo or 0)) > 0.01)
                        )

                        if mudou:
                            cursor.execute('''
                                UPDATE catalogo_imoveis SET
                                    preco = ?, avaliacao = ?, desconto_informado = ?,
                                    desconto_calculado = ?, financiavel = ?,
                                    modalidade_venda = ?, tipo_imovel = ?,
                                    area_privativa = ?, area_total = ?, area_terreno = ?,
                                    quartos = ?, banheiros = ?, vagas = ?,
                                    preco_m2_privativa = ?, preco_m2_total = ?, preco_m2_terreno = ?,
                                    smart_score = ?, faixa_preco = ?, faixa_desconto = ?,
                                    data_ultima_atualizacao = ?, snapshot_id_atualizacao = ?
                                WHERE id_imovel = ?
                            ''', (
                                row['preco'], row['avaliacao'], row['desconto_informado'],
                                row['desconto_calculado'],
                                int(row['financiavel']) if not pd.isna(row['financiavel']) else 0,
                                row['modalidade_venda'], row['tipo_imovel'],
                                row.get('area_privativa'), row.get('area_total'),
                                row.get('area_terreno'), row.get('quartos'),
                                row.get('banheiros'), row.get('vagas'),
                                row.get('preco_m2_privativa'), row.get('preco_m2_total'),
                                row.get('preco_m2_terreno'), row.get('smart_score'),
                                row.get('faixa_preco'), row.get('faixa_desconto'),
                                agora, snapshot_id, row['numero_imovel']
                            ))
                            contadores['atualizados'] += 1
                        else:
                            contadores['inalterados'] += 1

            # 5. MARCA COMO REMOVIDOS os imóveis que não apareceram na raspagem
            if removidos:
                for id_removido in removidos:
                    cursor.execute('''
                        UPDATE catalogo_imoveis SET
                            ativo = 0,
                            status = 'Removido/Arrematado',
                            data_remocao = ?,
                            data_ultima_atualizacao = ?
                        WHERE id_imovel = ?
                    ''', (agora, agora, id_removido))
                contadores['removidos'] = len(removidos)

            conn.commit()
            return contadores

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def obter_catalogo_ativo(self, filtros: Dict[str, Any] = None) -> pd.DataFrame:
        """Retorna DataFrame do catálogo ativo com filtros opcionais."""
        conn = sqlite3.connect(self.db_path)

        query = 'SELECT * FROM catalogo_imoveis WHERE ativo = 1'
        params = []

        if filtros:
            if filtros.get('cidade'):
                query += ' AND cidade_normalizada = ?'
                params.append(filtros['cidade'])
            if filtros.get('bairro'):
                query += ' AND bairro_normalizado = ?'
                params.append(filtros['bairro'])
            if filtros.get('tipo_imovel'):
                query += ' AND tipo_imovel = ?'
                params.append(filtros['tipo_imovel'])
            if filtros.get('financiavel') is not None:
                query += ' AND financiavel = ?'
                params.append(int(filtros['financiavel']))
            if filtros.get('smart_score_min'):
                query += ' AND smart_score >= ?'
                params.append(filtros['smart_score_min'])
            if filtros.get('desconto_min'):
                query += ' AND desconto_informado >= ?'
                params.append(filtros['desconto_min'])

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def obter_estatisticas_catalogo(self) -> Dict[str, Any]:
        """Retorna estatísticas do catálogo atual."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Totais
        cursor.execute('SELECT COUNT(*) FROM catalogo_imoveis WHERE ativo = 1')
        stats['total_ativos'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM catalogo_imoveis WHERE ativo = 0')
        stats['total_removidos'] = cursor.fetchone()[0]

        # Oportunidades Gold
        cursor.execute('''
            SELECT COUNT(*) FROM catalogo_imoveis
            WHERE ativo = 1 AND desconto_informado > 50 AND financiavel = 1 AND smart_score > 80
        ''')
        stats['oportunidades_gold'] = cursor.fetchone()[0]

        # Por tipo
        cursor.execute('''
            SELECT tipo_imovel, COUNT(*) FROM catalogo_imoveis WHERE ativo = 1
            GROUP BY tipo_imovel
        ''')
        stats['por_tipo'] = dict(cursor.fetchall())

        # Por modalidade
        cursor.execute('''
            SELECT modalidade_venda, COUNT(*) FROM catalogo_imoveis WHERE ativo = 1
            GROUP BY modalidade_venda
        ''')
        stats['por_modalidade'] = dict(cursor.fetchall())

        # Top bairros
        cursor.execute('''
            SELECT bairro_normalizado, COUNT(*) as qtd, AVG(smart_score) as score_medio
            FROM catalogo_imoveis WHERE ativo = 1
            GROUP BY bairro_normalizado
            ORDER BY qtd DESC LIMIT 10
        ''')
        stats['top_bairros'] = [
            {'bairro': r[0], 'quantidade': r[1], 'score_medio': round(r[2], 1) if r[2] else 0}
            for r in cursor.fetchall()
        ]

        conn.close()
        return stats

    def obter_logradouros_agrupados(self, cidade: str = None, bairro: str = None, top_n: int = 15) -> pd.DataFrame:
        """
        Retorna logradouros agrupados por endereco_limpo (nome da rua/condomínio).
        Usado para o gráfico "Top 15 Logradouros" sem duplicação por apto/bloco.
        """
        conn = sqlite3.connect(self.db_path)

        query = '''
            SELECT
                endereco_limpo as logradouro,
                COUNT(*) as quantidade,
                AVG(preco) as preco_medio,
                AVG(smart_score) as score_medio,
                AVG(desconto_informado) as desconto_medio,
                SUM(CASE WHEN financiavel = 1 THEN 1 ELSE 0 END) as financiaveis
            FROM catalogo_imoveis
            WHERE ativo = 1 AND endereco_limpo != ''
        '''
        params = []

        if cidade:
            query += ' AND cidade_normalizada = ?'
            params.append(cidade)
        if bairro:
            query += ' AND bairro_normalizado = ?'
            params.append(bairro)

        query += '''
            GROUP BY endereco_limpo
            ORDER BY quantidade DESC
            LIMIT ?
        '''
        params.append(top_n)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Formata preço médio
        df['preco_medio_fmt'] = df['preco_medio'].apply(lambda x: f"R$ {x:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        return df


def sincronizar_catalogo(df_processado: pd.DataFrame, snapshot_id: int,
                         db_path: str = 'data/historico_imoveis.db') -> Dict[str, int]:
    """
    Função de conveniência para integração direta no pipeline ETL.

    Uso no pipeline.py após transformação:
        from src.etl.sync import sincronizar_catalogo
        resultado_sync = sincronizar_catalogo(df_processado, snapshot_id)
        logger.info(f"Sync: {resultado_sync}")

    Returns:
        Dict com contadores: inseridos, atualizados, removidos, inalterados
    """
    sync = CatalogoSync(db_path)
    return sync.sincronizar(df_processado, snapshot_id)