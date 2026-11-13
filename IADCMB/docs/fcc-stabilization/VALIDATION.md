
## 2026-11-13 14:17:42 UTC — Validação após correção do lock

| Verificação | Resultado |
|---|---|
| Geração FCC | APROVADA |
| Exit code | 0 |
| Resposta esperada | FCC_LOCK_VALIDATION_OK |
| Aviso known_marketplaces lock | Não observado |
| Diretório .lock após execução | Ausente |
| JSON known_marketplaces | Válido |
| Event loop stall | 1145 ms, ocorrência isolada |
| Reinicialização de serviços | Não realizada |

Debug:
 /tmp/fcc-lock-validation-20261113-141633.log

Esta validação comprova o funcionamento da chamada curta após a correção.
Não comprova estabilidade de streaming prolongado nem resolução de
Connection lost mid-response.

## 2026-11-13 14:30:46 UTC — Regressão de streaming prolongado

| Indicador | Teste 1 | Teste 2 |
|---|---:|---:|
| Duração | 203s | 229s |
| Resposta | 21.247 bytes | 21.355 bytes |
| Exit code | 0 | 0 |
| Stream started | 1 | 1 |
| Connection lost mid-response | 0 | 0 |
| ECONNRESET | 0 | 0 |
| ETIMEDOUT | 0 | 0 |
| event-loop-stall | 2 | 2 |
| Lock presente após teste | Não | Não |

Logs:
- /tmp/fcc-stream-test-20261113-141846/debug.log
- /tmp/fcc-stream-test-20261113-142551/debug.log

Conclusão:
Duas gerações prolongadas concluídas sem erro de conexão registrado.
Não equivale à comprovação da cadência de entrega de cada chunk.
Os event-loop-stall permanecem pendentes de análise.

### Retificação — event-loop-stall

A contagem anterior de dois eventos por teste incluía a linha
de inicialização do detector. A contagem correta é um stall real
por execução:

- Teste 1: 963 ms, aproximadamente 4,7 segundos antes do primeiro chunk.
- Teste 2: 1.418 ms, aproximadamente 3,6 segundos antes do primeiro chunk.

Não há evidência de que esses stalls tenham ocorrido durante o streaming.
A causa permanece indeterminada.
