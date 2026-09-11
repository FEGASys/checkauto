#!/usr/bin/env bash
# CheckAuto - instalacao/reparo automatico. Rodar como root:
#   curl -fsSL https://raw.githubusercontent.com/FEGASys/checkauto/main/instalar.sh | bash
set -e

REPO="https://github.com/FEGASys/checkauto.git"
RAW="https://raw.githubusercontent.com/FEGASys/checkauto/main"
DIR="/opt/checkauto"

echo "== 1/6 usuario e pasta"
id -u checkauto >/dev/null 2>&1 || adduser --system --group --home "$DIR" --no-create-home checkauto
mkdir -p "$DIR"
if [ -d "$DIR/.git" ]; then
  cd "$DIR" && git pull --ff-only
else
  cd "$DIR" && git clone "$REPO" .
fi

echo "== 2/6 python"
command -v python3 >/dev/null || { apt-get update && apt-get install -y python3; }
dpkg -s python3-venv >/dev/null 2>&1 || { apt-get update && apt-get install -y python3-venv; }
[ -x "$DIR/venv/bin/python" ] || python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install --quiet --upgrade pip
"$DIR/venv/bin/pip" install --quiet -r "$DIR/requirements.txt"
chown -R checkauto:checkauto "$DIR"

echo "== 3/6 servico"
curl -fsSL "$RAW/checkauto.service" -o /etc/systemd/system/checkauto.service
systemctl daemon-reload
systemctl enable checkauto >/dev/null
systemctl restart checkauto
sleep 3
systemctl is-active checkauto

echo "== 4/6 teste local"
curl -fsS http://127.0.0.1:8010/saude && echo

echo "== 5/6 nginx"
curl -fsSL "$RAW/nginx-checkauto.conf" -o /etc/nginx/sites-available/checkauto
ln -sf /etc/nginx/sites-available/checkauto /etc/nginx/sites-enabled/checkauto
nginx -t
systemctl reload nginx

echo "== 6/6 teste via nginx"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "Host: srv1892358.hstgr.cloud" http://127.0.0.1/checklist/

echo
echo "PRONTO -> http://srv1892358.hstgr.cloud/checklist/"
echo "Para o cadeado (https), rode depois:"
echo "  certbot --nginx -d srv1892358.hstgr.cloud --redirect --agree-tos -m diretoria@fega.ind.br -n"
