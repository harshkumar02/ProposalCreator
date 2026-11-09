# Hosting ProposalCreator privately for free

The whole platform runs on **one Linux server** with Docker: Postgres, the FastAPI backend, n8n, the Next.js frontend, and Caddy as a reverse proxy. **Nothing listens on a public port.** You reach the app through a private network (Tailscale) or a login-protected tunnel (Cloudflare Access).

```
 your browser ──HTTPS──▶ Tailscale / Cloudflare ──▶ 127.0.0.1:8080 Caddy ─┬─ /api/*  ─▶ backend:8000 ─▶ Postgres
                                                                          ├─ /internal/* ─▶ 404 (n8n only)
                                                                          └─ everything else ─▶ frontend:3000
 backend ──webhook──▶ n8n:5678 ──/internal callbacks──▶ backend   (inside the Docker network only)
```

The n8n credential and workflows are provisioned automatically from this repo on every start (`n8n-init.sh`). Nobody needs to click anything in the n8n editor.

## 1. Get a free server

| Option | Cost | Notes |
|---|---|---|
| **Oracle Cloud Always Free** (recommended) | Free | Ampere ARM VM, up to 4 OCPU / 24 GB RAM. Create `VM.Standard.A1.Flex` with 2 OCPU / 12 GB and Ubuntu 24.04. If a region says "out of capacity", retry later or try another availability domain. Oracle may reclaim *idle* Always-Free instances; moving the account to Pay-As-You-Go keeps the same free limits and avoids that. |
| Any Linux VM or spare machine | — | Needs **≥ 2 GB RAM (4 GB recommended)** and 10 GB disk. 1 GB VMs (such as Google's free e2-micro) are too small for n8n. |
| Your own Windows PC | Free | Docker Desktop + WSL2. Only works while the PC is on, and it competes for memory with everything else. |

In the cloud firewall / security list, allow **only SSH (22)** inbound. Don't open 80, 443, 5678 or 8080; the access methods below don't need them.

## 2. Install and start

On the server:

```bash
curl -fsSL https://get.docker.com | sudo sh        # Docker Engine + compose plugin
sudo usermod -aG docker $USER && newgrp docker

git clone <your private repo URL> ProposalCreator  # or rsync/scp the folder
cd ProposalCreator/deploy
./setup.sh                                         # writes deploy/.env with random secrets
nano .env                                          # add GEMINI_API_KEY (and/or ANTHROPIC_API_KEY)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps       # wait until backend shows "healthy"
```

The first build takes a few minutes. Database migrations run automatically when the backend starts.

**Create the first account.** Sign-up is disabled in this mode:

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.cli create-user --email you@63sats.com --name "Your Name"
docker compose -f docker-compose.prod.yml exec backend python -m app.cli list-users
docker compose -f docker-compose.prod.yml exec backend python -m app.cli set-password --email you@63sats.com
```

Quick check from the server itself: `curl -s http://127.0.0.1:8080/health` should print `{"status":"healthy"}`.

## 3. Private access (pick one)

### A. Tailscale (recommended): private network, nothing public

Every user installs the Tailscale app and joins your tailnet. Check Tailscale's current free-plan user limit.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale serve --bg http://127.0.0.1:8080                 # the app
sudo tailscale serve --bg --https=5678 http://127.0.0.1:5678    # n8n editor (admins)
tailscale serve status
```

Open `https://<server-name>.<your-tailnet>.ts.net`. Tailscale provides the HTTPS certificate. Invite colleagues from the Tailscale admin console; anyone outside the tailnet can't even see the server.

### B. Cloudflare Tunnel + Access: browser only, email login

This needs a domain on Cloudflare (free plan). Cloudflare Zero Trust is free for small teams.

1. Zero Trust dashboard → **Networks → Tunnels → Create tunnel**. Install `cloudflared` on the server with the command it shows.
2. Add a public hostname, e.g. `proposals.yourdomain.com`, pointing to service `http://localhost:8080`.
3. **Access → Applications → Add** a self-hosted app for that hostname. Use a policy that allows only your team's email addresses (one-time PIN login).

Don't publish the n8n editor this way. Reach it with an SSH tunnel (option C).

### C. SSH tunnel only (just you)

```bash
ssh -L 8080:127.0.0.1:8080 -L 5678:127.0.0.1:5678 ubuntu@<server-ip>
# then open http://localhost:8080 (app) and http://localhost:5678 (n8n)
```

## 4. n8n editor

You don't need the n8n editor for normal use: the `rfp-analysis` workflow is imported and published automatically. Open it only to watch or debug executions. On the first visit, n8n asks you to create an owner account. Workflow changes belong in `n8n/workflows/*.json` in the repo, because they are re-imported on every restart and edits made only in the editor are overwritten.

## 5. Updating

```bash
cd ProposalCreator && git pull
cd deploy && docker compose -f docker-compose.prod.yml up -d --build
```

New database migrations and new or changed n8n workflows are applied automatically on restart.

## 6. Backups

```bash
./backup.sh                      # writes deploy/backups/proposalcreator-<time>.sql.gz, keeps the newest 14
crontab -e                       # daily at 02:30:
# 30 2 * * * /home/ubuntu/ProposalCreator/deploy/backup.sh >> /home/ubuntu/ProposalCreator/deploy/backups/backup.log 2>&1
```

Copy `deploy/backups/` **and `deploy/.env`** somewhere off the server, for example with `rclone` to Oracle Object Storage (free tier) or Google Drive. Without `.env` a backup can still be restored, but you will need new secrets and users will have to log in again. Restore commands are at the top of `backup.sh`.

## 7. Data privacy

Tender text is sent to the AI provider you configure (Gemini or Claude) for analysis. Before processing confidential government tenders, check that provider's data terms. On Google's Gemini API, free-tier usage may be used to improve Google's products, while paid usage (e.g. prepaid credits) is not. Confirm which tier your key is on in AI Studio. Nothing else leaves the server.

## Troubleshooting

| Symptom | Check |
|---|---|
| App doesn't load | `docker compose -f docker-compose.prod.yml ps` and `... logs -f caddy frontend backend` |
| "Workflow engine is not configured" | `N8N_SHARED_SECRET` is missing from `deploy/.env` |
| Analysis stays "Queued" / fails | `... logs -f n8n`. Look for `n8n-init:` lines at startup and `Publishing workflow` |
| Analysis fails with an API error | The provider key in `deploy/.env` is wrong. Restart after editing: `... up -d` |
| Server runs out of memory | Use ≥ 4 GB RAM, or add swap: `sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
