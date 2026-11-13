#!/usr/bin/env python3
"""
Radar Imobiliário RJ - Ponto de entrada principal.
Executa o pipeline ETL e opcionalmente inicia o dashboard.
"""
import sys
import argparse
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.etl.pipeline import executar_pipeline


def main():
    parser = argparse.ArgumentParser(
        description='Radar Imobiliário RJ - Plataforma de Inteligência Imobiliária'
    )
    parser.add_argument(
        '--config', '-c',
        default='config/settings.yaml',
        help='Caminho para arquivo de configuração YAML'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Força execução mesmo se arquivo não tiver mudado'
    )
    parser.add_argument(
        '--dashboard', '-d',
        action='store_true',
        help='Inicia dashboard Streamlit após ETL'
    )
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Mostra estatísticas do último processamento'
    )
    parser.add_argument(
        '--quality', '-q',
        action='store_true',
        help='Mostra relatório de qualidade do último processamento'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8501,
        help='Porta para o dashboard Streamlit (padrão: 8501)'
    )

    args = parser.parse_args()

    # Executa pipeline
    print("\n" + "=" * 60)
    print("RADAR IMOBILIÁRIO RJ - PIPELINE ETL")
    print("=" * 60)

    resultado, pipeline = executar_pipeline(config_path=args.config, forcar=args.force)

    if resultado.get('sucesso'):
        print(f"\n✅ PIPELINE EXECUTADO COM SUCESSO")
        print(f"   Snapshot ID: {resultado.get('snapshot_id')}")
        print(f"   Registros processados: {resultado.get('registros_processados', 0):,}")

        # Valores podem não estar presentes quando arquivo não mudou (skip)
        registros_validos = resultado.get('registros_validos')
        if registros_validos is not None:
            print(f"   Registros válidos: {registros_validos:,}")
            print(f"   Registros rejeitados: {resultado.get('registros_rejeitados', 0):,}")

        tempo = resultado.get('tempo_execucao_segundos')
        if tempo is not None:
            print(f"   Tempo: {tempo:.1f}s")

        # Mensagem de skip
        if 'mensagem' in resultado:
            print(f"   {resultado['mensagem']}")

        if args.stats:
            stats = pipeline.obter_estatisticas()
            print(f"\n📊 ESTATÍSTICAS:")
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"   {key}:")
                    for k, v in value.items():
                        print(f"     {k}: {v}")
                else:
                    print(f"   {key}: {value}")

        if args.quality:
            print(f"\n📋 RELATÓRIO DE QUALIDADE:")
            print(pipeline.exportar_relatorio_qualidade('txt'))

        if args.dashboard:
            print(f"\n🚀 Iniciando dashboard na porta {args.port}...")
            import subprocess
            subprocess.run([
                sys.executable, '-m', 'streamlit', 'run',
                'src/etl/dashboard/app.py',
                f'--server.port={args.port}',
                '--server.address=0.0.0.0'
            ])

    else:
        print(f"\n❌ PIPELINE FALHOU")
        print(f"   Erro: {resultado.get('erro')}")
        sys.exit(1)


if __name__ == '__main__':
    main()