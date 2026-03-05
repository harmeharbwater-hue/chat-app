# Deploy Chat App on Oracle Cloud (Always Free, 24/7)

This guide deploys your app on **Oracle Cloud Always Free** so it runs 24/7 at no cost. You get a real VM that stays on forever.

---

## Run locally (test before deploying)

From the project root:

**Option 1 – script (creates venv, installs deps, runs server):**
```bash
./run.sh
```

**Option 2 – manual:**
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser. The app uses SQLite by default (`./chat_app.db`). Optional: set `SECRET_KEY` and `ENCRYPTION_KEY` in a `.env` file for production-like testing.

**Option 3 – Docker (same as production):**
```bash
docker compose up --build
```
Then open **http://localhost:8080**.

---

## 1. Create an Oracle Cloud account

1. Go to [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
2. Sign up (credit card may be required for verification; Always Free resources do not incur charges).
3. Choose your **home region** (e.g. Phoenix, Frankfurt). Always Free VMs must stay in this region.

## 2. Create an Always Free VM

1. In the Oracle Cloud Console, go to **Menu → Compute → Instances**.
2. Click **Create Instance**.
3. **Name:** e.g. `chat-app`.
4. **Placement:** Keep default (your home region).
5. **Image and shape:**
   - **Image:** Pick a recent **Ubuntu** (e.g. Ubuntu 22.04).
   - **Shape:** Click **Change shape**:
     - For **AMD:** choose **VM.Standard.E2.1.Micro** (Always Free).
     - For **ARM:** choose **Ampere** and pick an Always Free A1 shape (e.g. 1 OCPU, 6 GB RAM).
6. **Networking:** Create a new VCN or use default. Ensure **Assign a public IPv4 address** is checked.
7. **Add SSH keys:** Upload your public SSH key or let Oracle generate a key pair (download the private key).
8. Click **Create**.

Wait until the instance state is **Running**. Note the **Public IP** and the **private key** you use to SSH.

## 3. Open HTTP (and HTTPS) in the firewall

1. Go to **Menu → Networking → Virtual cloud networks**.
2. Open the VCN used by your instance.
3. Click the **Default Security List** (or the one attached to the instance’s subnet).
4. **Ingress rules:** Add:
   - **Source:** `0.0.0.0/0`, **Port:** `80`, **Protocol:** TCP (for HTTP).
   - **Source:** `0.0.0.0/0`, **Port:** `443`, **Protocol:** TCP (for HTTPS, optional).
   - **Source:** `0.0.0.0/0`, **Port:** `8080`, **Protocol:** TCP (app port if you don’t use a reverse proxy yet).

Save the rules.

## 4. SSH into the VM and install Docker

```bash
ssh -i /path/to/your-private-key opc@<PUBLIC_IP>
```

(On Ubuntu images the user is often `ubuntu` instead of `opc` — use the username shown in the console.)

Install Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in (or run `newgrp docker`) so `docker` works without `sudo`.

## 5. Deploy the app on the VM

**Option A: Clone from Git (recommended)**

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/chat-app.git
cd chat-app
```

**Option B: Copy project with scp**

From your laptop:

```bash
scp -i /path/to/your-private-key -r /path/to/chat-app opc@<PUBLIC_IP>:~/chat-app
ssh -i /path/to/your-private-key opc@<PUBLIC_IP> "cd ~/chat-app && docker compose up -d --build"
```

**Set secrets and run (on the VM):**

```bash
cd ~/chat-app

# Generate and set strong secrets (run on your machine or the VM)
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(openssl rand -hex 32)

# Save them somewhere safe; then on the VM:
echo "SECRET_KEY=$SECRET_KEY" > .env
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env

docker compose up -d --build
```

The app listens on **port 8080**. Check:

```bash
curl http://localhost:8080/health
```

From your browser: `http://<PUBLIC_IP>:8080`.

## 6. Run on port 80 and restart on reboot (optional)

**Use port 80 and auto-restart:**

```bash
sudo tee /etc/systemd/system/chat-app.service << 'EOF'
[Unit]
Description=Chat App
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/opc/chat-app
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
```

If your SSH user is `ubuntu`, change `WorkingDirectory` to `/home/ubuntu/chat-app`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable chat-app.service
sudo systemctl start chat-app.service
```

**Listen on port 80:** edit `docker-compose.yml` and change the port mapping to `"80:8080"`, then:

```bash
docker compose up -d --force-recreate
```

(Or run a small reverse proxy like Caddy in front of the app; that’s the next step for HTTPS.)

## 7. HTTPS (optional)

- Use **Caddy** in the same VM as a reverse proxy: it gets a certificate automatically (e.g. with Let’s Encrypt). Point your domain’s A record to the VM’s public IP, then proxy to `localhost:8080`.
- Or put the VM behind **Cloudflare** (proxy on) and use Cloudflare’s SSL; you can keep HTTP on the VM and let Cloudflare handle HTTPS.

## Summary

| Step | Action |
|------|--------|
| 1 | Oracle Cloud Free Tier account, home region |
| 2 | Create Always Free VM (Ubuntu, E2.1.Micro or Ampere A1) |
| 3 | Security list: allow 80, 443, 8080 (or just 80/443 if using a proxy) |
| 4 | SSH in, install Docker (+ Compose plugin) |
| 5 | Clone/copy app, set `SECRET_KEY` and `ENCRYPTION_KEY` in `.env`, run `docker compose up -d --build` |
| 6 | Optional: systemd unit for restart on reboot, and port 80 |

Your app will run 24/7 on Oracle Always Free. Data is stored in the Docker volume `app_data` (SQLite under `/data` in the container).
