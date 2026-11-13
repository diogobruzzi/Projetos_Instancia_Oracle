"""
Módulo de extração - Leitura do CSV bruto.
"""
import pandas as pd
import hashlib
import os
from datetime import datetime
from typing import Tuple, Optional
from src.models.schemas import ImovelRaw


class CSVExtractor:
    """Extrator do arquivo CSV da Caixa."""

    def __init__(self, config: dict):
        self.config = config
        self.csv_config = config.get('csv', {})
        self.filepath = config.get('paths', {}).get('raw_data', 'data/raw/Lista_imoveis_RJ.csv')

    def extract(self) -> Tuple[pd.DataFrame, dict]:
        """
        Extrai dados do CSV bruto.
        Retorna: (DataFrame bruto, metadados do arquivo)
        """
        # Metadados do arquivo
        stat = os.stat(self.filepath)
        with open(self.filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        metadata = {
            'arquivo': self.filepath,
            'tamanho_bytes': stat.st_size,
            'modificado_em': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash_sha256': file_hash,
            'encoding': self.csv_config.get('encoding', 'latin-1'),
            'delimitador': self.csv_config.get('delimiter', ';'),
            'linhas_cabecalho': self.csv_config.get('skip_rows', 2),
            'extraido_em': datetime.now().isoformat(),
        }

        # Leitura do CSV
        df = pd.read_csv(
            self.filepath,
            sep=self.csv_config.get('delimiter', ';'),
            encoding=self.csv_config.get('encoding', 'latin-1'),
            skiprows=self.csv_config.get('skip_rows', 2),
            header=0,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )

        # Limpeza de nomes das colunas
        df.columns = df.columns.str.strip()

        # Strip em todas as colunas string
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        metadata['total_linhas'] = len(df)
        metadata['colunas'] = list(df.columns)

        return df, metadata

    def _calcular_hash(self) -> str:
        """Calcula SHA-256 do arquivo sem carregar o DataFrame completo."""
        with open(self.filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def verificar_mudanca(self, hash_anterior: Optional[str]) -> bool:
        """Verifica se o arquivo mudou desde a última extração."""
        if hash_anterior is None:
            return True
        hash_atual = self._calcular_hash()
        return hash_atual != hash_anterior


def extrair_csv_bruto(config: dict) -> Tuple[pd.DataFrame, dict]:
    """Função de conveniência para extração rápida."""
    extractor = CSVExtractor(config)
    return extractor.extract()