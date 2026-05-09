#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git curl

if [[ ! -d /opt/torch-proxy/.git ]]; then
  sudo mkdir -p /opt/torch-proxy
  sudo chown -R "$USER":"$USER" /opt/torch-proxy
  echo "Clone your repository into /opt/torch-proxy before continuing."
  exit 0
fi

cd /opt/torch-proxy
sudo cp deploy/torch-proxy.service /etc/systemd/system/torch-proxy.service
sudo systemctl daemon-reload
sudo systemctl enable torch-proxy

bash deploy/deploy.sh

sudo cp deploy/nginx-torch-proxy.conf /etc/nginx/sites-available/torch-proxy
sudo ln -sf /etc/nginx/sites-available/torch-proxy /etc/nginx/sites-enabled/torch-proxy
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1/health

echo "EC2 setup complete"
