#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/torch-proxy"
SERVICE_NAME="torch-proxy"
PYTHON_BIN="python3"

if [[ ! -d "$APP_DIR" ]]; then
  echo "App directory $APP_DIR does not exist"
  exit 1
fi

cd "$APP_DIR"

if [[ ! -d .venv ]]; then
  $PYTHON_BIN -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl enable "$SERVICE_NAME"

sleep 2
sudo systemctl --no-pager --full status "$SERVICE_NAME" || true
curl -fsS http://127.0.0.1:8080/health

echo "Deployment complete"
