# Google OAuth + code-server Setup Guide

Replica autenticação Google via OAuth2 Proxy + Caddy para code-server.

---

## Arquitetura

```
HTTPS (443) → Caddy → OAuth2 Proxy (4180) → code-server (8080)
                    ↑
              Google OAuth
```

- **Caddy**: Termina TLS, gerencia certificados ACME, forward_auth para OAuth2 Proxy
- **OAuth2 Proxy**: Autentica via Google, injeta headers de usuário
- **code-server**: Roda em rede Docker interna, sem auth próprio

---

## Pré-requisitos

- Domínio público apontando para o servidor (A/AAAA record)
- Google Cloud Project com OAuth 2.0 Client ID configurado
- Docker + Docker Compose
- Porta 80 e 443 abertas no firewall

---

## 1. Google Cloud Console — OAuth Client

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
3. **Application type**: Web application
4. **Authorized redirect URIs**:
   ```
   https://SEU-DOMINIO.com/oauth2/callback
   ```
5. Salve **Client ID** e **Client Secret**

---

## 2. Gerar Cookie Secret

```bash
openssl rand -base64 32 | tr -d '\n'
```

---

## 3. Estrutura de Diretórios

```
/opt/codeserver/
├── docker-compose.yml
├── caddy_config/
│   └── Caddyfile
├── oauth2_proxy_config/
│   └── config.cfg
└── coder_claude/          # (opcional) config Claude Code extension
```

---

## 4. docker-compose.yml

```yaml
services:
  caddy:
    image: caddy:2-alpine
    container_name: codeserver-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy_config/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - codeserver_net
    environment:
      - DOMAIN=SEU-DOMINIO.com
      - SUBDOMAIN=vscode
      - FQDN=vscode.SEU-DOMINIO.com
      - EMAIL=seu-email@gmail.com

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.8.0
    container_name: codeserver-oauth2-proxy
    restart: unless-stopped
    volumes:
      - ./oauth2_proxy_config:/etc/oauth2-proxy:ro
    networks:
      - codeserver_net
    environment:
      - OAUTH2_PROXY_CLIENT_ID=${OAUTH2_PROXY_CLIENT_ID}
      - OAUTH2_PROXY_CLIENT_SECRET=${OAUTH2_PROXY_CLIENT_SECRET}
      - OAUTH2_PROXY_COOKIE_SECRET=${OAUTH2_PROXY_COOKIE_SECRET}
      - OAUTH2_PROXY_EMAIL_DOMAINS=*
      - OAUTH2_PROXY_ALLOWED_EMAILS=seu-email@gmail.com
      - OAUTH2_PROXY_PROVIDER=google
      - OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180
      - OAUTH2_PROXY_UPSTREAMS=http://codeserver-app:8080
      - OAUTH2_PROXY_REDIRECT_URL=https://vscode.SEU-DOMINIO.com/oauth2/callback
      - OAUTH2_PROXY_SKIP_PROVIDER_BUTTON=true
      - OAUTH2_PROXY_INSECURE_OIDC_ALLOW_UNVERIFIED_EMAIL=true
      - OAUTH2_PROXY_SKIP_AUTH_REGEX=/ping

  codeserver:
    image: codercom/code-server:4.145.2
    container_name: codeserver-app
    restart: unless-stopped
    volumes:
      - /home/SEU-USUARIO/.config/code-server:/home/coder/.config/code-server:rw
      - /home/SEU-USUARIO/.local/share/code-server:/home/coder/.local/share/code-server:rw
      - /opt/codeserver/coder_claude:/home/coder/.claude:rw
      - /home/SEU-USUARIO/.local/bin:/home/coder/.local/bin:rw
      - /home/SEU-USUARIO:/home/coder/project:rw
    networks:
      - codeserver_net
    environment:
      - SUDO_PASSWORD=disabled
      - PROXY_DOMAIN=vscode.SEU-DOMINIO.com
      - PATH=/home/coder/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    working_dir: /home/coder/project
    user: "1001:1001"  # Ajuste para UID/GID do seu usuário host
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  caddy_data:
  caddy_config:

networks:
  codeserver_net:
    driver: bridge
```

---

## 5. caddy_config/Caddyfile

```caddyfile
{
	email seu-email@gmail.com
	admin off
}

vscode.SEU-DOMINIO.com {
	# Security headers
	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "SAMEORIGIN"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "camera=(), microphone=(), geolocation=()"
	}

	# Matcher: requests without auth cookie (exclude /oauth2/*)
	@noauth {
		not header Cookie *_oauth2_proxy*
		not path /oauth2/*
	}

	# Matcher: WebSocket upgrades
	@websocket {
		header Connection *Upgrade*
		header Upgrade websocket
	}

	# OAuth2-proxy callback - MUST NOT strip prefix
	route /oauth2/callback* {
		reverse_proxy codeserver-oauth2-proxy:4180
	}

	# OAuth2-proxy endpoints - strip /oauth2 prefix
	route /oauth2/* {
		uri strip_prefix /oauth2
		reverse_proxy codeserver-oauth2-proxy:4180
	}

	# Redirect unauthenticated to sign_in
	handle @noauth {
		respond 302
		header Location "/oauth2/sign_in?rd={uri}"
	}

	# Protected WebSocket - validate auth via cookie
	handle @websocket {
		reverse_proxy codeserver-app:8080
	}

	# Protected routes - forward_auth to OAuth2 Proxy
	route {
		forward_auth codeserver-oauth2-proxy:4180 {
			uri /oauth2/auth
			copy_headers X-Forwarded-User X-Forwarded-Email X-Forwarded-Groups X-Forwarded-Preferred-Username
		}
		reverse_proxy codeserver-app:8080
		header +Content-Security-Policy "connect-src 'self' wss: https:;"
	}
}
```

---

## 6. oauth2_proxy_config/config.cfg

```ini
# oauth2-proxy configuration
# See: https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/

# HTTP server address
http_address = "0.0.0.0:4180"

# Upstream (code-server)
upstreams = ["http://codeserver-app:8080"]

# Redirect URL after OAuth
redirect_url = "https://vscode.SEU-DOMINIO.com/oauth2/callback"

# Provider: google
provider = "google"

# Email domains allowed (empty = all)
email_domains = ["*"]

# Skip provider button (direct to Google)
skip_provider_button = true

# Insecure OIDC (for dev)
insecure_oidc_allow_unverified_email = true

# Cookie settings
cookie_secret = "${OAUTH2_PROXY_COOKIE_SECRET}"
cookie_expire = "168h"  # 7 days
cookie_refresh = "1h"
cookie_secure = true
cookie_httponly = true
cookie_samesite = "lax"

# SSL
ssl_upstream_insecure_skip_verify = true

# Logging
log_level = "info"

# Permitir /ping sem autenticação (healthcheck)
skip_auth_regex = ["/ping"]
```

---

## 7. .env (não versionar)

```bash
# /opt/codeserver/.env
OAUTH2_PROXY_CLIENT_ID=SEU_GOOGLE_CLIENT_ID
OAUTH2_PROXY_CLIENT_SECRET=SEU_GOOGLE_CLIENT_SECRET
OAUTH2_PROXY_COOKIE_SECRET=SEU_COOKIE_SECRET_32BYTES_BASE64
```

---

## 8. UID/GID do Usuário Host

No `docker-compose.yml`, ajuste `user: "UID:GID"` para corresponder ao seu usuário no host:

```bash
id seu-usuario
# Exemplo: uid=1001(seu-usuario) gid=1001(seu-usuario)
# → user: "1001:1001"
```

---

## 9. Deploy

```bash
cd /opt/codeserver
cp .env.example .env  # edite com seus valores
docker compose up -d
```

Verifique:
```bash
docker compose ps
docker compose logs -f caddy
docker compose logs -f oauth2-proxy
```

---

## 10. Validação

| Teste | Comando/URL |
|-------|-------------|
| HTTPS responde | `curl -k -I https://vscode.SEU-DOMINIO.com` → HTTP/2 302 |
| Redireciona OAuth | Location: `/oauth2/sign_in?rd=/` |
| Login Google funciona | Acesse no navegador |
| code-server carrega | Após login, VS Code abre |
| Healthcheck OK | `docker inspect codeserver-app --format '{{.State.Health.Status}}'` |

---

## 11. Troubleshooting

| Problema | Solução |
|----------|---------|
| `redirect_uri_mismatch` | Confira redirect URI no Google Cloud = `https://SEU-DOMINIO/oauth2/callback` |
| Certificado não emitido | Porta 80 aberta? DNS propagou? `docker compose logs caddy` |
| Loop de redirect | `cookie_secure=true` requer HTTPS; `insecure_oidc_allow_unverified_email=true` para dev |
| UID mismatch | Ajuste `user:` no compose para UID/GID do host |
| WebSocket falha | CSP `connect-src 'self' wss: https:` no Caddyfile |

---

## 12. Variáveis Importantes

| Variável | Origem | Obrigatória |
|----------|--------|-------------|
| `OAUTH2_PROXY_CLIENT_ID` | Google Cloud | Sim |
| `OAUTH2_PROXY_CLIENT_SECRET` | Google Cloud | Sim |
| `OAUTH2_PROXY_COOKIE_SECRET` | `openssl rand -base64 32` | Sim |
| `OAUTH2_PROXY_ALLOWED_EMAILS` | Seu email Google | Sim (restringe acesso) |
| `OAUTH2_PROXY_EMAIL_DOMAINS` | `*` ou domínio | Não |

---

## 13. Backup e Rollback

```bash
# Backup configs
tar -czf codeserver-backup-$(date +%Y%m%d).tar.gz /opt/codeserver

# Rollback
docker compose down
tar -xzf codeserver-backup-YYYYMMDD.tar.gz -C /
docker compose up -d
```

---

## 14. Checklist Nova Instância

- [ ] Domínio apontando para IP
- [ ] Google OAuth Client criado
- [ ] Redirect URI correto
- [ ] Cookie secret gerado
- [ ] `.env` preenchido
- [ ] `Caddyfile` com domínio/email corretos
- [ ] `config.cfg` com redirect_url correto
- [ ] `docker-compose.yml` com UID/GID, volumes, domínio
- [ ] Portas 80/443 abertas
- [ ] `docker compose up -d` sem erros
- [ ] HTTPS + login Google funcionam
- [ ] code-server abre em `/home/SEU-USUARIO`

---

**Baseado em produção**: `vscode.iadcmb.duckdns.org` rodando desde Nov 2026.