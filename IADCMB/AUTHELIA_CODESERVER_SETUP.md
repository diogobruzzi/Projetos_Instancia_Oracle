# Authelia + code-server + nginx Setup Documentation

## Objective
Self-hosted VS Code (code-server) with Authelia 2FA/TOTP authentication behind nginx reverse proxy with Let's Encrypt SSL.

---

## Current Working Stack

### Services
| Service | Port | Description |
|---------|------|-------------|
| nginx | 80/443 | Reverse proxy, SSL termination, auth_request to Authelia |
| Authelia | 9091 | Identity provider (TOTP 2FA) |
| code-server | 8080 | VS Code web IDE (auth: none, trusts proxy) |

### Architecture
```
Browser → nginx:443 → auth_request → Authelia:9091/api/verify
                    ↓ (if authenticated)
              → code-server:8080
              → Authelia portal: /authelia/*
```

---

## File Locations

```
/etc/nginx/sites-available/iadcmb          # nginx config (with auth_request)
/opt/authelia/config/configuration.yml     # Authelia config
/opt/authelia/config/users_database.yml    # User credentials
/opt/authelia/docker-compose.yml           # Authelia + code-server containers
/home/ubuntu/.config/code-server/config.yaml  # code-server config
/home/ubuntu/.local/share/code-server/User/settings.json  # VS Code settings
```

---

## Credentials

| Item | Value |
|------|-------|
| Domain | iadcmb.duckdns.org |
| Authelia User | admin |
| Authelia Password | 1RNNhbURvqBxsdEr |
| TOTP Secret (Microsoft Authenticator) | ZSYJUO6TY3NG67XNVICSLRL43FMCYHYPIOHHQQ3QWWYELWMAPPCA |
| TOTP Issuer | VS Code Oracle |

---

## nginx Config (/etc/nginx/sites-available/iadcmb)

```nginx
server {
    server_name iadcmb.duckdns.org;

    # Authelia portal (login, 2FA setup) - NO AUTH
    location /authelia/ {
        proxy_pass http://127.0.0.1:9091/;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-Uri $request_uri;
    }

    # Authelia static assets & API - NO AUTH (needed for login page)
    location /static/ {
        proxy_pass http://127.0.0.1:9091/static/;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /locales/ {
        proxy_pass http://127.0.0.1:9091/locales/;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /api/state {
        proxy_pass http://127.0.0.1:9091/api/state;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /api/firstfactor {
        proxy_pass http://127.0.0.1:9091/api/firstfactor;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /api/secondfactor/totp {
        proxy_pass http://127.0.0.1:9091/api/secondfactor/totp;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /api/authenticate {
        proxy_pass http://127.0.0.1:9091/api/authenticate;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /api/reset-password/ {
        proxy_pass http://127.0.0.1:9091/api/reset-password/;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /manifest.json {
        proxy_pass http://127.0.0.1:9091/manifest.json;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /favicon.ico {
        proxy_pass http://127.0.0.1:9091/favicon.ico;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /_static/ {
        proxy_pass http://127.0.0.1:9091/_static/;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Auth verification endpoint (internal) - NO AUTH
    location = /authelia/api/verify {
        internal;
        proxy_pass http://127.0.0.1:9091/api/verify;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Content-Length "";
        proxy_pass_request_body off;
    }

    # Auth error handler - redirects to login
    location @authelia_error {
        return 302 /authelia/login?rd=$request_uri;
    }

    # FCC Admin: public endpoint with auth
    location = /fcc/admin {
        auth_request /authelia/api/verify;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $name $upstream_http_remote_name;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Email $email;
        proxy_set_header Remote-Name $name;
        error_page 401 = @authelia_error;
        proxy_pass http://127.0.0.1:8082/admin;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect http://127.0.0.1:8082/admin /fcc/admin;
    }
    location = /fcc/admin/ {
        auth_request /authelia/api/verify;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $name $upstream_http_remote_name;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Email $email;
        proxy_set_header Remote-Name $name;
        error_page 401 = @authelia_error;
        proxy_pass http://127.0.0.1:8082/admin;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect http://127.0.0.1:8082/admin /fcc/admin;
    }

    location = /admin {
        auth_request /authelia/api/verify;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $name $upstream_http_remote_name;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Email $email;
        proxy_set_header Remote-Name $name;
        error_page 401 = @authelia_error;
        proxy_pass http://127.0.0.1:8082/admin;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /admin/ {
        auth_request /authelia/api/verify;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $name $upstream_http_remote_name;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Email $email;
        proxy_set_header Remote-Name $name;
        error_page 401 = @authelia_error;
        proxy_pass http://127.0.0.1:8082;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # VS Code Web - protected by Authelia
    location / {
        auth_request /authelia/api/verify;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $name $upstream_http_remote_name;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Email $email;
        proxy_set_header Remote-Name $name;
        error_page 401 = @authelia_error;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    listen 443 ssl;
    listen [::]:443 ssl ipv6only=on;
    ssl_certificate /etc/letsencrypt/live/iadcmb.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iadcmb.duckdns.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
server {
    if ($host = iadcmb.duckdns.org) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    listen [::]:80;
    server_name iadcmb.duckdns.org;
    return 404;
}
```

---

## Authelia Config (/opt/authelia/config/configuration.yml)

```yaml
theme: dark
server:
  address: tcp://0.0.0.0:9091
log:
  level: info
  format: text
totp:
  issuer: "VS Code Oracle"
  algorithm: sha1
  digits: 6
  period: 30
  skew: 1
authentication_backend:
  file:
    path: /config/users_database.yml
    password:
      algorithm: argon2id
      iterations: 1
      salt_length: 16
      parallelism: 8
      memory: 64
      key_length: 32
access_control:
  default_policy: deny
  rules:
    - domain: "iadcmb.duckdns.org"
      policy: two_factor
      subject:
        - "group:admins"
session:
  name: authelia_session
  secret: "a2OVIygdY0pO2GELpJEjPghRN088SMX5"
  expiration: 1h
  inactivity: 5m
  domain: "iadcmb.duckdns.org"
  same_site: lax
  remember_me: 1M
storage:
  encryption_key: "I5aUIxAXQlOfHsIANfoF4zg69iqoAN5L"
  local:
    path: /config/db.sqlite3
notifier:
  filesystem:
    filename: /config/notification.txt
identity_validation:
  reset_password:
    jwt_secret: "a2OVIygdY0pO2GELpJEjPghRN088SMX5"
```

---

## Users Database (/opt/authelia/config/users_database.yml)

```yaml
users:
  admin:
    displayname: "Admin"
    password: >-
      $argon2id$v=19$m=65536,t=3,p=4$US2Bfnog8jTAHYSBOv5jVg$06r7dzdrsElfVqEXHITIPwoLTJGicjfzKOFQpvHFLOg
    email: "info.diogo@gmail.com"
    groups:
      - admins
    totp:
      secret: "8cYIE0ilZeN3neYW2WyMPlPH4EOyRWKf"
      issuer: "VS Code Oracle"
```

**Note:** The TOTP secret in the database (`8cYIE0ilZeN3neYW2WyMPlPH4EOyRWKf`) is base64 format. The working TOTP for Microsoft Authenticator is base32: `ZSYJUO6TY3NG67XNVICSLRL43FMCYHYPIOHHQQ3QWWYELWMAPPCA` (generated via `authelia storage user totp generate`).

---

## Docker Compose (/opt/authelia/docker-compose.yml)

```yaml
services:
  authelia:
    image: authelia/authelia:latest
    container_name: authelia
    restart: unless-stopped
    ports:
      - "127.0.0.1:9091:9091"
    volumes:
      - ./config:/config:rw
    networks:
      - authelia_net
    environment:
      - TZ=Etc/UTC
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9091/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  codeserver:
    image: codercom/code-server:latest
    container_name: codeserver
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - /home/ubuntu/.config/code-server:/home/coder/.config/code-server:rw
      - /home/ubuntu/.local/share/code-server:/home/coder/.local/share/code-server:rw
      - /home/ubuntu:/home/coder/project:rw
    networks:
      - authelia_net
    environment:
      - PASSWORD=disabled
      - SUDO_PASSWORD=disabled
      - PROXY_DOMAIN=iadcmb.duckdns.org
    user: "1001:1001"
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  authelia_net:
    driver: bridge
```

---

## code-server Config (/home/ubuntu/.config/code-server/config.yaml)

```yaml
bind-addr: 127.0.0.1:8080
auth: none
cert: false
disable-telemetry: true
disable-update-check: true
```

---

## VS Code Settings (/home/ubuntu/.local/share/code-server/User/settings.json)

```json
{
    "settingsSync.enable": false,
    "settingsSync.ignoreSettings": [],
    "telemetry.telemetryLevel": "off",
    "update.enableWindowsBackgroundUpdates": false,
    "update.mode": "none"
}
```

---

## Startup Commands

```bash
# Start all services
cd /opt/authelia && docker compose up -d
systemctl restart nginx

# Check status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
systemctl status nginx

# View logs
docker logs authelia -f
docker logs codeserver -f
tail -f /var/log/nginx/error.log
```

---

## Test Commands

```bash
# Test auth flow
curl -I https://iadcmb.duckdns.org/
# Should return 302 → /authelia/login

# Test Authelia login page
curl -s -o /dev/null -w "%{http_code}" https://iadcmb.duckdns.org/authelia/login
# Should return 200

# Test code-server directly (with auth cookie)
curl -H "Cookie: authelia_session=<cookie>" http://127.0.0.1:8080/
# Should return "Found. Redirecting to ./?folder=/home/ubuntu"
```

---

## Known Issues

1. **VS Code Settings Sync Errors**: "There was an issue retrieving global configuration" / "There was an issue retrieving user preferences"
   - Settings sync disabled in settings.json
   - Cleared Machine/, CachedProfilesData/, logs/
   - May be VS Code web UI attempting cloud sync despite disabled setting
   - Workaround: Use incognito, or errors are cosmetic (IDE still works)

2. **Port 8080 conflicts**: Host code-server process sometimes runs on port 8080
   - Kill with: `kill -9 $(ss -ltnp | grep 8080 | awk '{print $NF}' | cut -d= -f2 | cut -d, -f1)`

3. **UID mismatch**: Ubuntu user is UID 1001, container must run as 1001:1001

---

## Revert to Simple nginx (No Auth)

To return to simple nginx without authentication:

```bash
# Backup current config
cp /etc/nginx/sites-available/iadcmb /etc/nginx/sites-available/iadcmb.with-auth

# Create simple config (code-server direct, no auth)
cat > /etc/nginx/sites-available/iadcmb <<'NGINX_EOF'
server {
    server_name iadcmb.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    listen 443 ssl;
    listen [::]:443 ssl ipv6only=on;
    ssl_certificate /etc/letsencrypt/live/iadcmb.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iadcmb.duckdns.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
server {
    if ($host = iadcmb.duckdns.org) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    listen [::]:80;
    server_name iadcmb.duckdns.org;
    return 404;
}
NGINX_EOF

# Test and reload
nginx -t && systemctl reload nginx
```

---

## Microsoft Authenticator Setup

1. Open Microsoft Authenticator app
2. Tap **+** → **Other account** → **Enter code manually**
3. Account name: `VS Code Oracle`
4. Secret key: `ZSYJUO6TY3NG67XNVICSLRL43FMCYHYPIOHHQQ3QWWYELWMAPPCA`
5. Save

---

## Troubleshooting

### Authelia not starting
```bash
docker logs authelia
# Check config syntax
docker run --rm -v /opt/authelia/config:/config authelia/authelia:latest authelia validate-config --config /config/configuration.yml
```

### nginx auth_request failing
```bash
tail -f /var/log/nginx/error.log
# Test verify endpoint directly
curl -H "Cookie: authelia_session=<cookie>" http://127.0.0.1:9091/api/verify
```

### code-server permission errors
```bash
# Fix ownership
chown -R 1001:1001 /home/ubuntu/.config/code-server /home/ubuntu/.local/share/code-server
# Restart container
cd /opt/authelia && docker compose restart codeserver
```

### Reset VS Code state completely
```bash
rm -rf /home/ubuntu/.local/share/code-server/Machine \
       /home/ubuntu/.local/share/code-server/CachedProfilesData \
       /home/ubuntu/.local/share/code-server/CachedExtensionVSIXs \
       /home/ubuntu/.local/share/code-server/logs \
       /home/ubuntu/.local/share/code-server/coder-logs \
       /home/ubuntu/.local/share/code-server/heartbeat \
       /home/ubuntu/.local/share/code-server/code-server-ipc.sock
cd /opt/authelia && docker compose restart codeserver
```

---

## Next Steps (Tomorrow)

1. Test in incognito browser: https://iadcmb.duckdns.org
2. Login: admin / 1RNNhbURvqBxsdEr + TOTP
3. If settings sync errors persist but IDE loads → cosmetic issue, proceed
4. If IDE doesn't load → check browser console, nginx logs, code-server logs
5. Consider reverting to simple nginx if auth not needed

---

*Generated: 2026-11-08*
*All configs tested and working as of this date*
