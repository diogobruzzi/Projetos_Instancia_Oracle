
## 2026-11-13 13:27:11 UTC — Preparação da documentação

- Criada/verificada a estrutura de documentação em /home/ubuntu/docs/fcc-stabilization.
- README.md inicializado, sem sobrescrever conteúdo anterior.
- Identificados quatro backups preexistentes.
- Nenhum serviço, container ou configuração de produção foi alterado.
- Nenhum backup foi removido ou sobrescrito.


## 2026-11-13 13:28:04 UTC — Diagnóstico inicial

- Executado levantamento somente leitura do ambiente.
- Relatório: DIAGNOSTICO-20261113-132802.md.
- Nenhum serviço ou container foi alterado.

## 2026-11-13 13:29:05 UTC — Análise do caminho FCC

- Coletados estado operacional da bridge, healthcheck, processos,
  conexões TCP e logs do relay e container.
- Relatório: ANALISE-CAMINHO-FCC-20261113-132905.md.
- Diagnóstico somente leitura; sem alterações de produção.

## 2026-11-13 13:30:01 UTC — Inspeção da implementação FCC

- Inspecionados código da bridge, relay, unidade systemd,
  rede, montagens e interface do cliente.
- Corrigida a localização da coleta do log do relay: dentro do container.
- Relatório: DETALHES-IMPLEMENTACAO-20261113-133000.md.
- Nenhuma alteração de produção executada.

## 2026-11-13 13:30:59 UTC — Teste das rotas FCC

- Testados FCC direto, relay 18083 e bridge 8082.
- Apenas GET /v1/models; sem geração ou alteração de serviços.
- Relatório: TESTE-ROTAS-20261113-133058.md.

## 2026-11-13 13:32:30 UTC — Teste real de streaming

- Executado um prompt curto pelo cliente FCC.
- Duração: 30 segundos.
- Código de saída: 0.
- Relatório: TESTE-STREAMING-20261113-133200.md.

## 2026-11-13 13:37:49 UTC — Auditoria FCC monitorada

- Prompt extenso executado pelo cliente FCC padrão.
- Duração: 127s.
- Código de saída: 0.
- Relatório: TESTE-AUDITORIA-20261113-133542.md.
- Arquivos brutos preservados em: /tmp/fcc-audit-test.1JtQwY.

## 2026-11-13 14:17:42 UTC — Correção do lock known_marketplaces.json

- Identificado diretório de lock vazio em ~/.claude/plugins/known_marketplaces.json.lock.
- Não havia processos Claude Code/FCC ativos na validação anterior.
- known_marketplaces.json validado como JSON íntegro.
- Backup criado em:
  backup-lock-20261113-141604/
- SHA-256 do JSON original e backup idênticos:
  16c2ef0e5d726828f878a844b69085f95ecd393b3a3c192f9650dccc73704477
- Diretório vazio removido com rmdir, sem remoção forçada.
- Teste posterior: FCC_LOCK_VALIDATION_OK, exit code 0.
- Aviso de aquisição do lock não apareceu no teste.
- Diretório de lock permaneceu ausente após o teste.
- Observado event-loop-stall isolado de 1145 ms; causa não investigada.
- Não houve reinicialização de serviços ou containers.
- Correção validada em teste pontual; recorrência ainda não descartada.

## 2026-11-13 14:30:46 UTC — Dois testes de streaming prolongado após correção do lock

- Teste 1: 203 segundos, exit code 0, resposta de 21.247 bytes.
- Teste 2: 229 segundos, exit code 0, resposta de 21.355 bytes.
- Ambos registraram Stream started uma vez.
- Nenhum registro de Connection lost mid-response.
- Nenhum ECONNRESET ou ETIMEDOUT encontrado.
- Nenhum aviso known_marketplaces.json lock.
- Diretório de lock permaneceu ausente após ambos os testes.
- Foram registrados dois event-loop-stall em cada execução.
- Nenhum serviço ou container foi reiniciado ou alterado.
- Resultado: duas gerações prolongadas concluídas com sucesso.
- Ressalva: os testes não mediram individualmente a cadência de entrega dos chunks.

## 2026-11-13 14:32:02 UTC — Precisão da contagem de event-loop-stall

Retificação da contagem registrada nos testes prolongados:

- O padrão event-loop-stall também aparece na linha de inicialização do detector.
- Teste 1: um stall real de 963 ms, às 14:18:59 UTC.
- Teste 2: um stall real de 1.418 ms, às 14:26:04 UTC.
- Ambos ocorreram antes do primeiro chunk da resposta.
- CPU registrada: 100 ms e 89 ms, respectivamente.
- blocked_write=false nos dois eventos.
- Major faults: zero nos dois eventos.
- Não há evidência de bloqueio durante o streaming.
- Causa dos stalls ainda não identificada.
