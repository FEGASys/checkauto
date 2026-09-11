# CheckAuto — instalação no VPS

App independente: serviço, pasta e banco próprios, sem tocar no sistema da
fábrica. Depois de instalado responde em:

**https://srv1892358.hstgr.cloud/checklist/**

| | |
|---|---|
| Código | https://github.com/FEGASys/checkauto (público) |
| Pasta no servidor | `/opt/checkauto` |
| Serviço systemd | `checkauto` — gunicorn em `127.0.0.1:8010` |
| Banco | SQLite em `/opt/checkauto/dados.db` |
| Usuário do sistema | `checkauto` (sem shell) |

O código já está no GitHub. Falta só rodar os blocos abaixo no servidor.

---

## Instalação

Abra o **Web console** (hPanel → VPS → Gerenciar → Visão geral → Web console) e
cole **um bloco por vez**, conferindo a saída antes de passar para o próximo.

### 1 — usuário, pasta e código

```bash
adduser --system --group --home /opt/checkauto --no-create-home checkauto
mkdir -p /opt/checkauto && cd /opt/checkauto
git clone https://github.com/FEGASys/checkauto.git .
ls -la
```

Devem aparecer `app.py`, `index.html`, `logo_preview.png` e `requirements.txt`.

### 2 — ambiente Python

```bash
apt update && apt install -y python3-venv
python3 -m venv /opt/checkauto/venv
/opt/checkauto/venv/bin/pip install --upgrade pip
/opt/checkauto/venv/bin/pip install -r /opt/checkauto/requirements.txt
chown -R checkauto:checkauto /opt/checkauto
```

### 3 — serviço systemd

```bash
cat > /etc/systemd/system/checkauto.service <<'EOF'
[Unit]
Description=CheckAuto - checklist de revisao de veiculos
After=network.target

[Service]
User=checkauto
Group=checkauto
WorkingDirectory=/opt/checkauto
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/checkauto/venv/bin/gunicorn --workers 2 --threads 4 --bind 127.0.0.1:8010 --timeout 60 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now checkauto
sleep 2
systemctl status checkauto --no-pager
curl -s http://127.0.0.1:8010/saude
```

Esperado: `active (running)` e a resposta `{"agora":...,"ok":true}`.

### 4 — nginx

```bash
cat > /etc/nginx/sites-available/checkauto <<'EOF'
server {
    listen 80;
    server_name srv1892358.hstgr.cloud;

    location = /checklist { return 301 /checklist/; }

    location /checklist/ {
        proxy_pass         http://127.0.0.1:8010/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        client_max_body_size 5m;
    }
}
EOF

ln -sf /etc/nginx/sites-available/checkauto /etc/nginx/sites-enabled/checkauto
nginx -t && systemctl reload nginx
```

Já dá para abrir: **http://srv1892358.hstgr.cloud/checklist/**

### 5 — HTTPS (cadeado)

```bash
certbot --nginx -d srv1892358.hstgr.cloud --redirect --agree-tos -m diretoria@fega.ind.br -n
nginx -t && systemctl reload nginx
```

Pronto: **https://srv1892358.hstgr.cloud/checklist/**

### 6 — backup diário

```bash
echo 'cp /opt/checkauto/dados.db /root/backups/checkauto-$(date +\%F).db' >> /usr/local/bin/backup-db.sh
echo 'find /root/backups -name "checkauto-*.db" -mtime +21 -delete' >> /usr/local/bin/backup-db.sh
```

---

## Atualizar depois

Suba o arquivo novo no GitHub (arrastar e commitar) e rode no servidor:

```bash
cd /opt/checkauto && git pull && systemctl restart checkauto
```

## Comandos úteis

```bash
systemctl status checkauto
journalctl -u checkauto -n 60 --no-pager
systemctl restart checkauto
apt install -y sqlite3
sqlite3 /opt/checkauto/dados.db "SELECT placa, modelo, datetime(atualizado_em/1000,'unixepoch','-3 hours') FROM revisoes ORDER BY atualizado_em DESC LIMIT 10;"
```

## Se quiser proteger com senha depois

```bash
apt install -y apache2-utils
htpasswd -c /etc/nginx/.htpasswd-checkauto oficina     # pede a senha
```

E acrescentar dentro do bloco `location /checklist/`:

```
auth_basic "Checklist";
auth_basic_user_file /etc/nginx/.htpasswd-checkauto;
```

---

## Observações

- **Hoje não tem senha:** quem tiver o link vê, edita e apaga revisões.
- O app não encosta nos bancos `fegasys` nem `chatwoot_production`.
- O nome da fábrica não aparece em nada visível do app.
- No celular: abrir o link no Chrome/Safari e usar *Adicionar à tela de início*
  para virar ícone.
