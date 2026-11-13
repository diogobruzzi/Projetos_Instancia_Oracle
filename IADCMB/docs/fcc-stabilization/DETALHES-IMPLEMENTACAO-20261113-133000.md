# Detalhes de implementação do FCC

- Data: 2026-11-13 13:30:00 UTC
- Método: somente leitura

## 1. Código da bridge no host
```python
#!/usr/bin/env python3

import socket
import socketserver
import subprocess
import threading

PORT = 8082
UPSTREAM_PORT = 18083
CONTAINER = "codeserver-app"


def get_container_ip():
    return subprocess.check_output(
        [
            "docker", "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            CONTAINER
        ],
        text=True,
        timeout=5
    ).strip()


def forward(source, destination):
    try:
        while True:
            data = source.recv(65536)
            if not data:
                break
            destination.sendall(data)
    except OSError:
        pass
    finally:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        upstream = None

        try:
            ip = get_container_ip()

            upstream = socket.create_connection(
                (ip, UPSTREAM_PORT),
                timeout=10
            )

            upstream.settimeout(None)

            thread = threading.Thread(
                target=forward,
                args=(self.request, upstream),
                daemon=True
            )

            thread.start()
            forward(upstream, self.request)
            thread.join(timeout=3)

        except Exception as error:
            print(f"Bridge error: {error}", flush=True)

        finally:
            if upstream:
                upstream.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


server = Server(("127.0.0.1", PORT), Handler)

print(
    f"FCC bridge listening on 127.0.0.1:{PORT}",
    flush=True
)

server.serve_forever()
```

## 2. Código do relay dentro do container
```python
import socket
import socketserver
import threading

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            upstream = socket.create_connection(("127.0.0.1", 8082), timeout=5)
            client = self.request

            def forward(source, destination):
                try:
                    while True:
                        data = source.recv(65536)
                        if not data:
                            break
                        destination.sendall(data)
                except OSError:
                    pass
                finally:
                    try:
                        destination.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass

            t = threading.Thread(
                target=forward,
                args=(client, upstream),
                daemon=True
            )
            t.start()
            forward(upstream, client)
            t.join(timeout=2)
            upstream.close()
        except OSError:
            pass

server = socketserver.ThreadingTCPServer(
    ("172.18.0.4", 18083), Handler
)
server.daemon_threads = True
server.serve_forever()
```

## 3. Log correto do relay dentro do container
```text
```

## 4. Unidade systemd da bridge
```ini
# /etc/systemd/system/fcc-host-bridge.service
[Unit]
Description=Free Claude Code Host Bridge
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/sbin/fcc-host-bridge.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 5. Rede e montagens do container
```text
NetworkMode=container:0d78547fe9a7ac9d36d6293e19ba66a9f523c6eb1167b10f149661fa3bd7a623
Mounts=[{"Type":"bind","Source":"/home/ubuntu/.local/share/uv/tools/free-claude-code","Destination":"/opt/fcc","Mode":"ro","RW":false,"Propagation":"rprivate"},{"Type":"bind","Source":"/opt/codeserver/fcc-loopback-relay.py","Destination":"/tmp/fcc-loopback-relay.py","Mode":"ro","RW":false,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/ubuntu/.fcc","Destination":"/home/fcc/.fcc","Mode":"rw","RW":true,"Propagation":"rprivate"}]
Networks={}
```

## 6. Nomes de variáveis de ambiente do servidor FCC
```text
FCC_CONFIG_DIR
HOME
HOSTNAME
LANG
NVIDIA_NIM_API_KEY
PATH
PWD
PYTHONPATH
PYTHON_SHA256
PYTHON_VERSION
```

## 7. Clientes FCC ativos
```text
```

## 8. Versão e ajuda do cliente
```text
2.1.322 (Claude Code)
Usage: claude [options] [command] [prompt]

Claude Code - starts an interactive session by default, use -p/--print for
non-interactive output

Arguments:
  prompt                                Your prompt

Options:
  --add-dir <directories...>            Additional directories to allow tool
                                        access to
  --agent <agent>                       Agent for the current session. Overrides
                                        the 'agent' setting.
  --agents <json-or-file>               JSON object defining custom agents, or
                                        with --print the path to a file that
                                        holds one (e.g. '{"reviewer":
                                        {"description": "Reviews code",
                                        "prompt": "You are a code reviewer"}}')
  --allow-dangerously-skip-permissions  Enable bypassing all permission checks
                                        as an option, without it being enabled
                                        by default. Recommended only for
                                        sandboxes with no internet access.
  --allowedTools, --allowed-tools <tools...>
      Comma or space-separated list of tool names to allow (e.g. "Bash(git *)
      Edit")
  --append-system-prompt <prompt>       Append a system prompt to the default
                                        system prompt
  --autocompact <auto|tokens>           Auto-compact window size (auto, or
                                        100k–1M tokens)
  --ax-screen-reader                    Render screen-reader friendly output
                                        (flat text, no decorative borders or
                                        animations).
  --bg, --background                    Start the session in the background and
                                        return immediately. Prints the id that
                                        `claude attach`, `logs`, `stop` and `rm`
                                        take; `claude agents` lists them. With
                                        --resume <session-id>, continues that
                                        session in the background under the same
                                        ID, or starts a copy and says so when
                                        the session is already running
  --bare                                Minimal mode: skip hooks (those defined
                                        in settings and by installed plugins;
                                        features built into Claude Code are
                                        unaffected), LSP, plugin sync,
                                        attribution, auto-memory, background
                                        prefetches, keychain reads, and
                                        CLAUDE.md auto-discovery. Sets
                                        CLAUDE_CODE_SIMPLE=1. Anthropic auth is
                                        strictly ANTHROPIC_API_KEY or
                                        apiKeyHelper via --settings (OAuth and
                                        keychain are never read). 3P providers
                                        (Bedrock/Vertex/Foundry) use their own
                                        credentials. Skills still resolve via
                                        /skill-name. Explicitly provide context
                                        via: --system-prompt[-file],
                                        --append-system-prompt[-file], --add-dir
                                        (CLAUDE.md dirs), --mcp-config,
                                        --settings, --agents, --plugin-dir.
  --betas <betas...>                    Beta headers to include in API requests
                                        (API key users only)
  --brief                               Enable SendUserMessage tool for
                                        agent-to-user communication
  --chrome                              Enable Claude in Chrome integration
  --cloud [description|session_id|url]  Create a cloud session with the given
                                        description, or attach to an existing
                                        one by session ID or claude.ai/code URL
  -c, --continue                        Continue the most recent conversation in
                                        the current directory
  --dangerously-skip-permissions        Bypass all permission checks.
                                        Recommended only for sandboxes with no
                                        internet access.
  -d, --debug [filter]                  Enable debug mode with optional category
                                        filtering (e.g., --debug=hooks,mcp or
                                        --debug='!hooks,!mcp')
  --debug-file <path>                   Write debug logs to a specific file path
                                        (implicitly enables debug mode)
  --desktop                             Open in the Claude Desktop app instead
                                        of the terminal (with --continue or
                                        --resume <id> to pick the session)
  --disable-slash-commands              Disable all skills and commands
  --disallowedTools, --disallowed-tools <tools...>
      Comma or space-separated list of tool names to deny (e.g. "Bash(git *)
      Edit")
  --effort <level>                      Effort level for the current session
                                        (low, medium, high, xhigh, max)
  --environment <environment_id>        Create a new cloud session that runs on
                                        the given self-hosted environment
                                        (ccpool_...).
  --exclude-dynamic-system-prompt-sections
      Move per-machine sections (cwd, env info, memory paths, git status) from
      the system prompt into the first user message. Improves cross-user
      prompt-cache reuse. Only applies with the default system prompt (ignored
      with --system-prompt). (default: false)
  --fallback-model <model>              Enable automatic fallback to specified
                                        model(s) when the default model is
                                        overloaded or not available. Accepts a
                                        comma-separated list to try each in
                                        order. Re-tries the primary at the start
                                        of each user turn.
  --file <specs...>                     File resources to download at startup.
```

## 9. Limites
- Nenhum pedido de geração foi enviado.
- Nenhum serviço foi reiniciado.
- Nenhuma configuração foi alterada.
- Valores de variáveis de ambiente não foram coletados.
