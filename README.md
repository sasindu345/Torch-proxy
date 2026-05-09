# Torch-proxy

ProxyMaze'26 challenge implementation workspace.

## EC2 Access (Current Working Setup)

You are already using this working connection:

```bash
ssh -i /Users/oneionei/Downloads/proxymaze-key.pem ubuntu@65.1.35.247
```

Important detail:
- Instance OS user is `ubuntu` (not `ec2-user`).

## Quick SSH Config (Recommended)

Add this to your local `~/.ssh/config` file:

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

## One-Time Permission Fix (if needed)

If SSH says the key permissions are too open:

```bash
chmod 400 /Users/oneionei/Downloads/proxymaze-key.pem
```

## Basic Connection Verification

After connecting, you should see prompt similar to:

```bash
ubuntu@ip-172-31-35-59:~$
```

Then run:

```bash
whoami
hostname -I
```

Expected:
- `whoami` => `ubuntu`
- `hostname -I` => shows private instance IP(s)

## If Connection Fails, Check These First

1. EC2 instance is running.
2. Public IP is still `65.1.35.247` (it can change if no Elastic IP).
3. Security Group allows inbound `SSH (22)` from your IP.
4. You are using the correct key file: `proxymaze-key.pem`.
5. Local network/firewall is not blocking outbound SSH.

## Project Paths (Local)

- Workspace root: `/Users/oneionei/MyProjects/proxy_maze`
- App repo: `/Users/oneionei/MyProjects/proxy_maze/Torch-proxy`
- Challenge PDF: `/Users/oneionei/MyProjects/proxy_maze/ProxyMaze26_Challenge.pdf`

