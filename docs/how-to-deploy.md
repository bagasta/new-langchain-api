# How to Deploy the LangChain API with systemd and Nginx

These steps provision a single-node deployment where `uvicorn` runs behind Nginx and is supervised by systemd. Commands assume Ubuntu 22.04, but any modern Linux distro with Python 3.11+, systemd, and Nginx will work.

## 1. Prepare the Server

- Update base packages and install required tooling:
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx redis-server postgresql-client
  ```
- Create an application user (recommended) and log in:
  ```bash
  sudo adduser --system --group --home /opt/langchain-api langchain
  sudo usermod -a -G www-data langchain        # allow Nginx to read static files if needed
  sudo -iu langchain
  ```

## 2. Fetch the Application

```bash
cd /opt/langchain-api
git clone https://github.com/your-org/Langchain-API-new.git
cd Langchain-API-new
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If you deploy from a private repository, configure SSH or a deployment key first. For future upgrades you’ll reuse the `langchain` user, activate the virtual environment, `git pull`, and `pip install -r requirements.txt`.

## 3. Configure Environment Variables

Create a production copy of the sample configuration:

```bash
cp .env.example .env.prod
nano .env.prod   # or your preferred editor
```

At minimum populate:
- `SECRET_KEY`
- `DATABASE_URL` (e.g. `postgresql://user:pass@db-host:5432/langchain_api`)
- `REDIS_URL`
- Required API keys (OpenAI, Google OAuth, etc.)

Store the final values outside the repo so systemd can load them securely:

```bash
sudo tee /etc/langchain-api-new.env >/dev/null <<'EOF'
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@db-host:5432/langchain_api
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=replace-me
OPENAI_API_KEY=sk-...
# add any other keys from .env.prod
EOF
sudo chown root:root /etc/langchain-api-new.env
sudo chmod 640 /etc/langchain-api-new.env
```

Update `/etc/langchain-api-new.env` whenever secrets change. Do not commit production secrets to git.

## 4. Initialize the Database

Ensure the target PostgreSQL instance is reachable, then run migrations:

```bash
source /opt/langchain-api/Langchain-API-new/.venv/bin/activate
cd /opt/langchain-api/Langchain-API-new
alembic upgrade head
```

If you manage Redis locally, enable and start it now (`sudo systemctl enable --now redis-server`).

## 5. Install the systemd Service

Copy the provided unit file and tailor it to your environment:

```bash
sudo cp deploy/systemd/langchain-api-new.service /etc/systemd/system/langchain-api-new.service
sudo chown root:root /etc/systemd/system/langchain-api-new.service
sudo chmod 644 /etc/systemd/system/langchain-api-new.service
```

Edit `/etc/systemd/system/langchain-api-new.service`:
- Set `User` and `Group` to the deployment account (`langchain` if you followed the steps above).
- Point `WorkingDirectory` to `/opt/langchain-api/Langchain-API-new`.
- Ensure the `Environment` path references the virtual environment (e.g. `/opt/langchain-api/Langchain-API-new/.venv/bin`).
- Confirm the `EnvironmentFile` line reads `EnvironmentFile=-/etc/langchain-api-new.env`.
- Adjust `ExecStart` only if you want to bind to a different host/port.

Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now langchain-api-new.service
sudo systemctl status langchain-api-new.service
```

The app should now listen on `127.0.0.1:8123`. Check logs with `journalctl -u langchain-api-new.service -efu`.

## 6. Configure Nginx as a Reverse Proxy

Create a webroot for Certbot challenges before enabling HTTPS:

```bash
sudo mkdir -p /var/www/certbot
sudo chown www-data:www-data /var/www/certbot
```

Copy the provided Nginx template:

```bash
sudo cp deploy/nginx/new-langchain.conf /etc/nginx/sites-available/langchain-api.conf
sudo nano /etc/nginx/sites-available/langchain-api.conf
```

Update:
- `server_name` to your domain (`api.example.com`).
- Any log paths or limits you want to customize.
- Leave the HTTPS `listen` directives commented until certificates exist.

Enable the site and test the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/langchain-api.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Obtain TLS Certificates

Run Certbot in webroot mode to keep the Nginx template compatible with automated renewals:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d api.example.com
```

After certificates are issued, uncomment the HTTPS `listen` directives in `/etc/nginx/sites-available/langchain-api.conf` and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Certbot installs a timer for renewals automatically (`systemctl list-timers certbot*`). Verify renewal with `sudo certbot renew --dry-run`.

## 8. Smoke Test the Deployment

- Confirm the app responds:
  ```bash
  curl -I https://api.example.com/health
  ```
- Check the reverse proxy logs (`sudo tail -f /var/log/nginx/new-langchain.error.log`).
- Inspect application logs if anything fails (`journalctl -u langchain-api-new.service -efu`).

## 9. Ongoing Maintenance

- **Deploying updates**
  ```bash
  sudo systemctl stop langchain-api-new.service
  sudo -iu langchain bash -lc 'cd /opt/langchain-api/Langchain-API-new && git pull && source .venv/bin/activate && pip install -r requirements.txt && alembic upgrade head'
  sudo systemctl start langchain-api-new.service
  ```
- **Backups**: Schedule PostgreSQL dumps and copy `/etc/langchain-api-new.env`.
- **Monitoring**: Add health checks to your uptime service and monitor Nginx/systemd logs.

Following these steps results in a secure, systemd-managed FastAPI service fronted by Nginx with automatic TLS renewal.
