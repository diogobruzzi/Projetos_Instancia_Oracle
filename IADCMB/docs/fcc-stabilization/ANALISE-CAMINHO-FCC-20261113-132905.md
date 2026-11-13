# Análise do caminho de conexão do FCC

- Data: 2026-11-13 13:29:05 UTC
- Método: somente leitura

## 1. Configuração operacional da bridge
```text
ActiveState=active
SubState=running
FragmentPath=/etc/systemd/system/fcc-host-bridge.service
Restart=always
MainPID=1498869
ExecStart={ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 /usr/local/sbin/fcc-host-bridge.py ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }
StandardOutput=journal
StandardError=inherit
```

## 2. Estado e healthcheck do container FCC
```text
Status=running RestartCount=0 StartedAt=2026-11-11T21:43:47.197079658Z Health=healthy
Healthcheck={"Test":["CMD","python3","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8082/v1/models', timeout=5)"],"Interval":30000000000,"Timeout":10000000000,"StartPeriod":30000000000,"Retries":3}
```

## 3. Processos dentro do container FCC
```text
UID                 PID                 PPID                C                   STIME               TTY                 TIME                CMD
root                1502944             1502918             0                   Nov11               ?                   00:04:43            python3 /opt/fcc/bin/fcc-server --host 127.0.0.1 --port 8082
root                1502960             1502944             0                   Nov11               ?                   00:00:00            /usr/local/bin/python3 -c from multiprocessing.resource_tracker import main;main(8)
root                1504994             1502918             0                   Nov11               ?                   00:00:00            sh -c python3 /tmp/fcc-loopback-relay.py >> /tmp/fcc-loopback-relay.log 2>&1
root                1505000             1504994             0                   Nov11               ?                   00:00:13            python3 /tmp/fcc-loopback-relay.py
```

## 4. Conexões TCP relacionadas
```text
```

## 5. Log do relay
```text
Arquivo /tmp/fcc-loopback-relay.log não encontrado ou inacessível.
```

## 6. Eventos recentes do serviço bridge
```text
-- No entries --
```

## 7. Últimos registros do FCC container
```text
INFO:     127.0.0.1:46786 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34926 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34610 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58024 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:42308 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:60242 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43928 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34372 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:47646 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46832 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33022 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50306 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:51522 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:38054 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50248 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:36116 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:41692 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46982 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:59776 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:54146 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58776 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:38612 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:55770 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:41444 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:48260 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:56350 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:60710 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:32932 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33912 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:36912 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43114 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46504 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43724 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58032 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:38292 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:54284 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:35630 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50188 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:57324 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46732 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33022 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50022 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:53086 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50094 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:44920 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:32846 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:56182 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:47788 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:44378 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:47284 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:48606 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:38216 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:59056 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:36298 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:42360 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34234 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58136 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43266 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34912 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:41310 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:51478 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:52628 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:55864 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:41890 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46758 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33362 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:57824 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43994 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:51522 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:42632 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33370 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:46798 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43782 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33402 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:44464 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:54018 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:34180 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:60100 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:39088 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58654 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:41020 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:44722 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:55264 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:57988 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:55602 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:47562 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:55000 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:58730 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:43766 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50208 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:42668 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:60672 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:59538 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:50852 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:53032 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:33978 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:48938 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:45442 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:60806 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:47870 - "GET /v1/models HTTP/1.1" 200 OK
```

## 8. Limites
- Nenhum processo foi encerrado.
- Nenhum serviço ou container foi reiniciado.
- Nenhuma configuração foi modificada.
- Nenhuma requisição de geração de texto foi disparada.
