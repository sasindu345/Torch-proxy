# Torch-proxy

ProxyMaze API service (FastAPI) with CI/CD and EC2 hosting setup.

## Current status

- Core API + monitoring implemented.
- Evaluator-focused behavior validated with curl.
- CI workflow added.
- Manual EC2 deploy workflow added.

## EC2 SSH (your current working access)

```bash
ssh -i /Users/oneionei/Downloads/proxymaze-key.pem ubuntu@65.1.35.247
```

Optional `~/.ssh/config`:

```sshconfig
Host proxymaze
  HostName 65.1.35.247
  User ubuntu
  IdentityFile /Users/oneionei/Downloads/proxymaze-key.pem
```

Then connect with:

```bash
ssh proxymaze
```

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Health check:

```bash
curl -sS http://127.0.0.1:8080/health
```

## CI/CD added

### CI

File: `.github/workflows/ci.yml`

Runs on push to `main` and PR:
- install dependencies
- compile check
- smoke-run app and curl `/health`

### CD (manual trigger)

File: `.github/workflows/deploy-ec2.yml`

Trigger: GitHub Actions `workflow_dispatch`

It SSHes to EC2, pulls `main`, and runs:

```bash
bash deploy/ec2-setup.sh
```

## Hosting files added

- `deploy/deploy.sh`
- `deploy/ec2-setup.sh`
- `deploy/torch-proxy.service`
- `deploy/nginx-torch-proxy.conf`

## Manual steps you must do

## 1) Push code to GitHub main

```bash
git push origin main
```

## 2) Add GitHub Action secrets

In GitHub repo: `Settings -> Secrets and variables -> Actions`, add:

- `EC2_HOST` = `65.1.35.247`
- `EC2_USER` = `ubuntu`
- `EC2_SSH_KEY` = full private key content from `proxymaze-key.pem`
- `REPO_SSH_URL` = SSH clone URL of this repo (example: `git@github.com:<you>/<repo>.git`)

## 3) Prepare EC2 once

SSH into server and run:

```bash
ssh proxymaze
sudo mkdir -p /opt/torch-proxy
sudo chown -R ubuntu:ubuntu /opt/torch-proxy
```

Then clone repo to `/opt/torch-proxy` (if not already cloned):

```bash
cd /opt
git clone <YOUR_REPO_SSH_URL> torch-proxy
cd /opt/torch-proxy
```

Run one-time setup:

```bash
bash deploy/ec2-setup.sh
```

## 4) Install systemd service file

```bash
sudo cp /opt/torch-proxy/deploy/torch-proxy.service /etc/systemd/system/torch-proxy.service
sudo systemctl daemon-reload
sudo systemctl enable --now torch-proxy
```

## 5) Install nginx config

```bash
sudo cp /opt/torch-proxy/deploy/nginx-torch-proxy.conf /etc/nginx/sites-available/torch-proxy
sudo ln -sf /etc/nginx/sites-available/torch-proxy /etc/nginx/sites-enabled/torch-proxy
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 6) Verify app from server

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1/health
```

## 7) Open inbound security group ports

- `22` (SSH)
- `80` (HTTP)
- `443` (HTTPS, if enabling TLS later)

## 8) Trigger deployment from GitHub

- Open `Actions -> Deploy to EC2`
- Click `Run workflow`

## Useful ops commands

```bash
sudo systemctl status torch-proxy
sudo journalctl -u torch-proxy -n 100 --no-pager
sudo systemctl restart torch-proxy
sudo systemctl status nginx
```

## Post-deploy smoke test

Run one command from your laptop:

```bash
bash deploy/smoke-test.sh http://65.1.35.247
```

This validates core evaluator endpoints:
- `/health`
- `/config` (POST + GET)
- `/proxies` (POST + GET + single + history + DELETE)
- `/metrics`
- `/alerts`

## Manual mandatory tasks only

1. Keep EC2 Security Group `SSH 22` reachable from GitHub Actions runners (or SSH deploy times out).
2. Revoke leaked PATs immediately and replace with a fresh token in `REPO_SSH_URL` secret.
3. Trigger Deploy workflow after each push to `main`.
