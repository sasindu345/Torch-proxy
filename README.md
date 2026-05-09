# Torch-proxy

ProxyMaze API service (FastAPI) with CI/CD and EC2 hosting setup.

## Current status

- Core API + monitoring implemented.
- Evaluator-focused behavior validated with curl.
- CI workflow added.
- Auto deploy to EC2 enabled on push to `main` (manual trigger kept as backup).

## Submission Ready

- Public Base URL: `https://proxymazegmora.duckdns.org`
- Health endpoint: `https://proxymazegmora.duckdns.org/health`
- Config endpoint: `https://proxymazegmora.duckdns.org/config`
- HTTPS enabled with Let's Encrypt certificate.
- CI/CD: push to `main` triggers CI + deploy automatically.

Quick verification:

```bash
curl -sS https://proxymazegmora.duckdns.org/health
curl -sS https://proxymazegmora.duckdns.org/config
bash deploy/smoke-test.sh https://proxymazegmora.duckdns.org
```

## System Architecture & Walkthrough

ProxyMaze utilizes an event-driven **FastAPI** + **aiohttp** architecture built to maximize concurrency and maintain strict consistency:
- **Global Lock State**: All endpoint reads and background monitor writes share a centralized `app_state` lock, ensuring APIs always return consistent truth.
- **Event-Driven Monitoring**: Mutating the proxy pool (`POST /proxies` or `DELETE`) triggers an `asyncio.Event`, forcing immediate re-evaluations to satisfy sub-second alert threshold requirements.
- **Strict Webhook Serializer**: Webhook deliveries utilize a per-URL lock (`url_locks`) combined with custom `301 Redirect` handling to guarantee that `alert.fired` and `alert.resolved` payloads arrive sequentially and with their `POST` bodies intact, bypassing default `aiohttp` redirect payload drops.



## Secrets and Variables (Team Guide)

This project does **not** use a local `.env` file for runtime today.

Runtime configuration is managed by:
- API endpoint `POST /config` (for `check_interval_seconds`, `request_timeout_ms`)
- System/service files (`systemd`, `nginx`)
- GitHub Actions secrets for CI/CD deployment

### GitHub Actions secrets required

Set in: `GitHub Repo -> Settings -> Secrets and variables -> Actions`

- `EC2_HOST`
  - Example: `65.1.35.247`
  - Purpose: target server for deploy workflow.

- `EC2_USER`
  - Example: `ubuntu`
  - Purpose: SSH user for deploy workflow.

- `EC2_SSH_KEY`
  - Value: private key content used to SSH into EC2.
  - Purpose: authentication for GitHub Actions SSH deploy.

- `REPO_SSH_URL`
  - Current use: repository clone URL used on EC2 during deploy.
  - If using PAT in URL, rotate token regularly.

### Sensitive data policy

- Do **not** commit tokens, keys, or passwords to the repository.
- Do **not** paste PAT/keys in code, README, or issues.
- If a token is leaked, revoke immediately and replace secret.

### Optional local `.env` note

If team later introduces `.env`, add:
- `.env` to `.gitignore`
- `.env.example` with placeholders only
- clear variable docs in this README

### What teammates need to update safely

1. Pull latest `main`.
2. Confirm GitHub secrets are present and valid.
3. Push to `main` (auto deploy runs).
4. Verify deploy status in Actions.
5. Run smoke test:
   - `bash deploy/smoke-test.sh https://proxymazegmora.duckdns.org`

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

### CD (automatic + manual)

File: `.github/workflows/deploy-ec2.yml`

Trigger:
- automatic on push to `main`
- manual via `workflow_dispatch` (backup)

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

## 8) Deployment trigger

- Default: push to `main` and deploy runs automatically.
- Optional manual backup: `Actions -> Deploy to EC2 -> Run workflow`.

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
3. After each push to `main`, verify GitHub Actions deploy status is green.
