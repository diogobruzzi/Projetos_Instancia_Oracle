"""
Pipeline ETL Principal - Orquestra extração, transformação, validação e carga.
"""
import os
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from src.etl.extract import CSVExtractor
from src.etl.transform import DataTransformer
from src.etl.validate import DataValidator
from src.etl.load import DataLoader
from src.models.schemas import RelatorioQualidade


class ETLPipeline:
    """Pipeline ETL completo para o Radar Imobiliário RJ."""

    def __init__(self, config_path: str = 'config/settings.yaml'):
        self.config_path = config_path
        self.config = self._carregar_config(config_path)
        self._setup_logging()

        # Componentes
        self.extractor = CSVExtractor(self.config)
        self.transformer = DataTransformer(self.config)
        self.validator = DataValidator(self.config)
        self.loader = DataLoader(self.config)

        # Estado
        self.snapshot_id: Optional[int] = None
        self.df_raw: Optional[pd.DataFrame] = None
        self.df_processado: Optional[pd.DataFrame] = None
        self.relatorio_qualidade: Optional[RelatorioQualidade] = None
        self.metadata_extracao: Optional[Dict] = None

    def _carregar_config(self, config_path: str) -> Dict[str, Any]:
        """Carrega configuração do YAML."""
        if not os.path.exists(config_path):
            # Configuração padrão se arquivo não existir
            return {
                'paths': {
                    'raw_data': 'data/raw/Lista_imoveis_RJ.csv',
                    'processed_dir': 'data/processed',
                    'historico_db': 'data/historico_imoveis.db'
                },
                'csv': {
                    'encoding': 'latin-1',
                    'delimiter': ';',
                    'skip_rows': 2
                },
                'validation': {
                    'price_min': 1000,
                    'price_max': 50000000,
                    'evaluation_min': 1000,
                    'evaluation_max': 50000000,
                    'discount_min': 0,
                    'discount_max': 100,
                    'max_price_vs_evaluation_ratio': 2.0,
                    'max_discount_diff_pct': 5.0
                },
                'enrichment': {
                    'extract_area_privativa': True,
                    'extract_area_total': True,
                    'extract_area_terreno': True,
                    'extract_quartos': True,
                    'extract_banheiros': True,
                    'extract_vagas': True,
                    'extract_tipo_imovel': True,
                    'calculate_price_per_m2': True,
                    'calculate_discount_calculated': True,
                    'calculate_score_oportunidade': True
                }
            }

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        """Configura logging."""
        log_config = self.config.get('logging', {})
        log_file = log_config.get('file', 'logs/pipeline.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def executar(self, forcar: bool = False) -> Dict[str, Any]:
        """
        Executa pipeline completo.
        Retorna dicionário com resultados e métricas.
        """
        self.logger.info("=" * 60)
        self.logger.info("INICIANDO PIPELINE ETL - RADAR IMOBILIÁRIO RJ")
        self.logger.info("=" * 60)

        inicio = datetime.now()

        try:
            # 1. Verifica se arquivo mudou
            if not forcar and not self._verificar_mudanca():
                self.logger.info("Arquivo não alterado desde última execução. Pulando...")
                return self._carregar_ultimo_resultado()

            # 2. Extração
            self.logger.info("ETAPA 1/5: Extração do CSV bruto...")
            self.df_raw, self.metadata_extracao = self.extractor.extract()
            self.logger.info(f"  → {len(self.df_raw):,} registros extraídos")

            # 3. Transformação
            self.logger.info("ETAPA 2/5: Transformação e enriquecimento...")
            self.snapshot_id = self._gerar_snapshot_id()
            self.df_processado = self.transformer.transform(self.df_raw, self.snapshot_id)
            self.logger.info(f"  → {len(self.df_processado):,} registros processados")

            # 4. Validação
            self.logger.info("ETAPA 3/5: Validação de qualidade...")
            self.relatorio_qualidade = self.validator.validar_dataframe(self.df_processado)
            self.logger.info(
                f"  → Válidos: {self.relatorio_qualidade.registros_validos:,} | "
                f"Rejeitados: {self.relatorio_qualidade.registros_rejeitados:,} | "
                f"Com avisos: {self.relatorio_qualidade.registros_com_avisos:,}"
            )

            # 5. Carga (arquivos processados)
            self.logger.info("ETAPA 4/5: Salvamento dados processados...")
            arquivos_salvos = self.loader.salvar_processado(
                self.df_processado, self.snapshot_id, self.metadata_extracao
            )
            for fmt, path in arquivos_salvos.items():
                self.logger.info(f"  → {fmt}: {path}")

            # 6. Carga (banco histórico)
            self.logger.info("ETAPA 5/5: Atualização banco histórico...")
            snapshot_meta = self._preparar_metadata_snapshot()
            snapshot_id_db = self.loader.salvar_snapshot_historico(
                self.df_processado, snapshot_meta
            )
            self.logger.info(f"  → Snapshot {snapshot_id_db} salvo no histórico")

            # 7. Relatório de qualidade
            self.logger.info("Salvando relatório de qualidade...")
            self.loader.salvar_relatorio_qualidade(self.relatorio_qualidade, self.snapshot_id)

            tempo_total = (datetime.now() - inicio).total_seconds()
            self.logger.info(f"PIPELINE CONCLUÍDO EM {tempo_total:.1f}s")

            return {
                'sucesso': True,
                'snapshot_id': self.snapshot_id,
                'tempo_execucao_segundos': tempo_total,
                'registros_brutos': len(self.df_raw),
                'registros_processados': len(self.df_processado),
                'registros_validos': self.relatorio_qualidade.registros_validos,
                'registros_rejeitados': self.relatorio_qualidade.registros_rejeitados,
                'registros_com_avisos': self.relatorio_qualidade.registros_com_avisos,
                'arquivos_salvos': arquivos_salvos,
                'snapshot_id_db': snapshot_id_db,
                'metadata': self.metadata_extracao,
            }

        except Exception as e:
            self.logger.error(f"ERRO NO PIPELINE: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao_segundos': (datetime.now() - inicio).total_seconds(),
            }

    def _verificar_mudanca(self) -> bool:
        """Verifica se o arquivo CSV mudou."""
        hash_anterior = self._obter_ultimo_hash()
        return self.extractor.verificar_mudanca(hash_anterior)

    def _obter_ultimo_hash(self) -> Optional[str]:
        """Obtém hash do último snapshot processado."""
        snapshots = self.loader.listar_snapshots()
        if snapshots:
            return snapshots[0].get('metadata_origem', {}).get('hash_sha256')
        return None

    def _gerar_snapshot_id(self) -> int:
        """Gera ID sequencial para o snapshot."""
        snapshots = self.loader.listar_snapshots()
        if snapshots:
            return max(s.get('snapshot_id', 0) for s in snapshots) + 1
        return 1

    def _preparar_metadata_snapshot(self) -> Dict[str, Any]:
        """Prepara metadados para salvar no banco histórico."""
        return {
            'data_hora': datetime.now().isoformat(),
            'arquivo_origem': self.metadata_extracao.get('arquivo', ''),
            'hash_sha256': self.metadata_extracao.get('hash_sha256', ''),
            'total_registros': len(self.df_processado),
            'registros_validos': self.relatorio_qualidade.registros_validos,
            'registros_rejeitados': self.relatorio_qualidade.registros_rejeitados,
            'status_importacao': 'SUCESSO',
        }

    def _carregar_ultimo_resultado(self) -> Dict[str, Any]:
        """Carrega resultado da última execução bem-sucedida."""
        df_latest = self.loader.carregar_latest()
        if df_latest is not None:
            return {
                'sucesso': True,
                'snapshot_id': self._gerar_snapshot_id() - 1,
                'registros_processados': len(df_latest),
                'arquivos_salvos': {'latest': 'data/processed/imoveis_rj_latest.parquet'},
                'mensagem': 'Carregado último snapshot (arquivo não alterado)'
            }
        return {'sucesso': False, 'erro': 'Nenhum snapshot anterior encontrado'}

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do último processamento."""
        if self.df_processado is None:
            return {}

        stats = self.validator.gerar_relatorio_estatistico(self.df_processado)
        stats['qualidade'] = {
            'total': self.relatorio_qualidade.total_registros,
            'validos': self.relatorio_qualidade.registros_validos,
            'rejeitados': self.relatorio_qualidade.registros_rejeitados,
            'com_avisos': self.relatorio_qualidade.registros_com_avisos,
        }
        return stats

    def exportar_relatorio_qualidade(self, formato: str = 'txt') -> str:
        """Exporta relatório de qualidade em diferentes formatos."""
        if self.relatorio_qualidade is None:
            return "Nenhum relatório disponível"

        if formato == 'txt':
            return self.relatorio_qualidade.resumo()
        elif formato == 'df':
            return self.relatorio_qualidade.to_dataframe()
        elif formato == 'json':
            import json
            return json.dumps({
                'resumo': {
                    'total': self.relatorio_qualidade.total_registros,
                    'validos': self.relatorio_qualidade.registros_validos,
                    'rejeitados': self.relatorio_qualidade.registros_rejeitados,
                    'com_avisos': self.relatorio_qualidade.registros_com_avisos,
                },
                'erros': self.relatorio_qualidade.erros_por_tipo,
                'avisos': self.relatorio_qualidade.avisos_por_tipo,
            }, ensure_ascii=False, indent=2)
        else:
            return self.relatorio_qualidade.resumo()


def executar_pipeline(config_path: str = 'config/settings.yaml', forcar: bool = False) -> Tuple[Dict[str, Any], 'ETLPipeline']:
    """Função de conveniência para executar pipeline. Retorna (resultado, pipeline)."""
    pipeline = ETLPipeline(config_path)
    resultado = pipeline.executar(forcar=forcar)
    return resultado, pipeline


if __name__ == '__main__':
    # Execução direta
    resultado = executar_pipeline()
    print(f"\nResultado: {resultado}")