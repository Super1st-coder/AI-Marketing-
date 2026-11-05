# Self-hosted OpenVPN on Google Cloud (Terraform)

> Deploy a production-ready OpenVPN gateway on a GCP Compute Engine VM so your
> dev/QA team can securely access private cloud resources and internal services
> via an encrypted tunnel. Includes split-horizon DNS for `*.hiluca.com` domains.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Directory Structure](#directory-structure)
3. [Deployment](#deployment)
4. [Generating Client Profiles](#generating-client-profiles)
5. [Connecting – macOS](#connecting--macos)
6. [Connecting – Windows](#connecting--windows)
7. [Connecting – Linux](#connecting--linux)
8. [Internal Services (DNS)](#internal-services-dns)
9. [Architecture](#architecture)
10. [Security Recommendations](#security-recommendations)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Terraform | 1.5+ | `brew install terraform` |
| Google Cloud SDK (`gcloud`) | any recent | `brew install --cask google-cloud-sdk` |
| GCP Project | — | [console.cloud.google.com](https://console.cloud.google.com) |

### Enable Required GCP APIs

```bash
gcloud services enable compute.googleapis.com --project=YOUR_PROJECT_ID
```

### Authenticate Terraform with GCP

```bash
gcloud auth application-default login
```

Required IAM roles on the project:

- `roles/compute.networkAdmin`
- `roles/compute.securityAdmin`
- `roles/compute.instanceAdmin.v1`
- `roles/iam.serviceAccountUser`

---

## Directory Structure

```
terraform/openvpn/
├── main.tf                    # All GCP resources (VPC, firewall, VM, VPC peering)
├── variables.tf               # Input variable declarations
├── outputs.tf                 # Outputs: IP, SSH command, next steps
├── terraform.tfvars           # Your values (gitignored)
├── terraform.tfvars.example   # Copy → terraform.tfvars and fill in
├── update-adk-proxy.sh        # Live update script: apply nginx+dnsmasq changes to running VM
└── README.md                  # This file
```

---

## Deployment

### 1. Configure variables

```bash
cd terraform/openvpn
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id, region, SSH key, allowed IPs, etc.
```

> **Never commit `terraform.tfvars`** – it contains your SSH key and IP allowlist.

### 2. Initialize

```bash
terraform init
```

### 3. Review the plan

```bash
terraform plan
```

### 4. Apply

```bash
terraform apply
```

Terraform prints `vpn_public_ip`, `ssh_command`, and step-by-step `next_steps` when done.
The startup script takes **3–5 minutes** after the VM boots to complete.

### 5. Verify startup completed

Via GCP Console SSH or your terminal:

```bash
ssh ubuntu@<vpn_public_ip>
sudo tail -3 /var/log/openvpn-setup.log
# Must end with: === OpenVPN setup complete ===
```

### Teardown

```bash
terraform destroy
```

> The static IP is released on destroy. Update your `.ovpn` files if you re-deploy.

---

## Generating Client Profiles

The startup script automatically installs `/root/make-client-ovpn.sh` on the server.
It creates the client certificate **and** the `.ovpn` bundle in a single command.

### Add a team member

SSH into the VPN server (GCP Console or terminal):

```bash
# Default 365-day certificate
sudo bash /root/make-client-ovpn.sh alice

# Custom expiration (90 days for a contractor)
sudo bash /root/make-client-ovpn.sh contractor 90

# 2-year certificate for core team
sudo bash /root/make-client-ovpn.sh bob 730
```

### Download the `.ovpn` to your Mac

Run on your **local machine**:

```bash
scp ubuntu@<vpn_public_ip>:/root/alice.ovpn ~/Downloads/
```

### Revoke a certificate

```bash
ssh ubuntu@<vpn_public_ip>
cd /etc/openvpn/easy-rsa
sudo ./easyrsa revoke alice
sudo ./easyrsa gen-crl
sudo cp pki/crl.pem /etc/openvpn/server/
```

Then add `crl-verify /etc/openvpn/server/crl.pem` to `/etc/openvpn/server/server.conf`
and restart: `sudo systemctl restart openvpn-server@server`.

---

## Connecting – macOS

1. Install **Tunnelblick**: https://tunnelblick.net/downloads.html
2. Double-click `alice.ovpn` – Tunnelblick imports it automatically.
3. Click **Connect** from the menu bar icon.

Alternatively use **OpenVPN Connect**:
https://openvpn.net/client/client-connect-vpn-for-mac-os/

---

## Connecting – Windows

1. Install **OpenVPN Connect** for Windows:
   https://openvpn.net/client/client-connect-vpn-for-windows/
2. Open OpenVPN Connect → **Import Profile** → select `alice.ovpn`.
3. Click **Connect**.

---

## Connecting – Linux

```bash
sudo apt-get install openvpn   # Debian/Ubuntu
sudo dnf install openvpn       # Fedora/RHEL

# Connect (foreground)
sudo openvpn --config alice.ovpn

# Or as a systemd service
sudo cp alice.ovpn /etc/openvpn/client/alice.conf
sudo systemctl enable --now openvpn-client@alice
```

---

## Internal Services (DNS)

When connected to the VPN, the server acts as a **split-horizon DNS** via `dnsmasq`.
All hostnames below resolve to `10.128.0.12` and are proxied by `edge-nginx` with
real HTTPS/SSL — no `/etc/hosts` modifications needed on the client.

### Frontend & API

| Hostname | Service | Container | Port |
|----------|---------|-----------|------|
| `https://dev.hiluca.com` | Frontend DEV | `hiluca-frontend-dev` | `8080` |
| `https://qa.hiluca.com` | Frontend QA | `hiluca-frontend-qa` | `8082` |
| `https://api-dev.hiluca.com` | Sinergia API DEV | `hiluca-sinergia-dev` | `60002` |
| `https://api-qa.hiluca.com` | Sinergia API QA | `hiluca-sinergia-qa` | `60004` |

### Backend & Internal Tools

| Hostname | Service | Container | Port |
|----------|---------|-----------|------|
| `https://fury-dev.hiluca.com` | Fury AI backend DEV | `hiluca-fury-dev` | `61000` |
| `https://n8n-dev.hiluca.com` | n8n Workflow DEV | `hiluca-n8n-dev` | `25678` |
| `https://n8n-qa.hiluca.com` | n8n Workflow QA | `hiluca-n8n-qa` | `25680` |
| `https://strapi-dev.hiluca.com` | Strapi CMS DEV | `hiluca-strapi-dev` | `21337` |
| `https://strapi-qa.hiluca.com` | Strapi CMS QA | `hiluca-strapi-qa` | `21339` |
| `https://langfuse-dev.hiluca.com` | Langfuse AI Observability | `hiluca-fury-langfuse-web-dev` | `3000` |
| `https://minio-dev.hiluca.com` | MinIO Object Storage Console | `hiluca-minio-dev` | `9090` |
| `https://qdrant-dev.hiluca.com` | Qdrant Vector DB Dashboard | `hiluca-qdrant-dev` | `6333` |

### ADK Cloud Run (Google Ads Multi-Agent)

| Hostname | Service | Protocolo |
|----------|---------|----------|
| `http://adk.hiluca.internal` | ADK Web UI (Google Ads Multi-Agent) | HTTP (VPN-only) |

> **Cómo funciona el proxy ADK:**
> `adk.hiluca.internal` no apunta a `10.128.0.12` (el servidor privado) sino a `10.8.0.1`
> (el propio servidor VPN). El **nginx en el servidor VPN** recibe el request, agrega un
> `Authorization: Bearer <GCP identity token>` obtenido del Metadata Server (compute SA),
> y lo reenvía a `hiluca-adk-dev-*.run.app` desde dentro del VPC.
> Cloud Run con `ingress=INTERNAL_ONLY` acepta este request porque nginx está dentro del VPC.
>
> El token se refresca automáticamente cada 45 minutos vía cron en el servidor VPN:
> ```
> */45 * * * * /usr/local/bin/refresh-adk-token.sh >> /var/log/adk-token.log 2>&1
> ```

> All other DNS queries (e.g. `google.com`) are forwarded to `8.8.8.8` normally.

**How it works:**
```
VPN client → DNS 10.8.0.1 (dnsmasq on VPN server)
  fury-dev.hiluca.com → 10.128.0.12
  → edge-nginx :443 → hiluca-fury-dev :61000   (real SSL cert)
```

### Applying nginx changes

The updated `nginx.conf` lives at `terraform/openvpn/nginx.conf` in this repo.
To deploy changes to the running `edge-nginx` container on the server:

```bash
# 1. Copy the updated config into the running container
docker cp nginx.conf edge-nginx:/etc/nginx/nginx.conf

# 2. Test the config for syntax errors
docker exec edge-nginx nginx -t

# 3. Reload without downtime
docker exec edge-nginx nginx -s reload
```

### Applying dnsmasq changes (after `terraform apply`)

If you re-provision the VPN server with the updated `main.tf`, the new hostnames
are baked into the startup script and require no manual action. For an existing
server, SSH in and update `/etc/dnsmasq.conf` manually, then:

```bash
sudo systemctl restart dnsmasq
```

---

## Architecture

```
Internet
    |
    | UDP 1194 (from allowed_admin_cidrs + 35.235.240.0/20 for GCP IAP)
    |
+---------------------------+
|   OpenVPN Gateway VM      |  ← tag: vpn-server
|   Static IP: x.x.x.x     |    e2-micro, Ubuntu 22.04
|   10.10.0.x (vpn-subnet) |
|   tun0: 10.8.0.1          |
|   dnsmasq on 10.8.0.1:53  |
+---------------------------+
    |  VPN pool: 10.8.0.0/24 (pushed to clients)
    |  Routes pushed: 10.10.0.0/24, 10.128.0.0/20
    |
    |  VPC Peering (vpn-network ↔ default)
    |
+---------------------------+
|  default VPC              |
|  10.128.0.0/20            |
|                           |
|  [10.128.0.12]            |  ← All hiluca.com services
|    edge-nginx :80/:443    |
|    hiluca-frontend-dev    |
|    hiluca-frontend-qa     |
|    hiluca-sinergia-dev    |
|    hiluca-sinergia-qa     |
|    ... (see docker ps)    |
+---------------------------+
```

**Resources created by Terraform:**

| # | Resource | Description |
|---|----------|-------------|
| 1 | `google_compute_network` | VPC `vpn-network` |
| 2 | `google_compute_subnetwork` | Subnet `vpn-subnet` (10.10.0.0/24) |
| 3 | `google_compute_firewall` | Allow UDP 1194 from `allowed_admin_cidrs` |
| 4 | `google_compute_firewall` | Allow SSH 22 from `allowed_admin_cidrs` |
| 5 | `google_compute_firewall` | Allow VPN pool (10.8.0.0/24) to `private-vm` tagged VMs |
| 6 | `google_compute_firewall` | Allow VPN pool to reach `default` VPC |
| 7 | `google_compute_address` | Static external IP |
| 8 | `google_compute_instance` | Ubuntu 22.04 VPN gateway VM |
| 9 | `google_compute_network_peering` | `vpn-network` → `default` |
| 10 | `google_compute_network_peering` | `default` → `vpn-network` |

---

## Security Recommendations

| # | Recommendation |
|---|----------------|
| 1 | **Restrict `allowed_admin_cidrs`** to your team's known static IPs. Never use `0.0.0.0/0` for SSH. |
| 2 | **Set certificate expiration** using the second argument: `make-client-ovpn.sh <name> <days>`. Default is 365. |
| 3 | **Revoke certificates** immediately when a team member leaves (see Revoke section above). |
| 4 | **Use `e2-small` or larger** for more than 5 simultaneous VPN clients. `e2-micro` has CPU burst limits. |
| 5 | **Backup the PKI** (`/etc/openvpn/easy-rsa/pki/`) to a GCS bucket after first boot. |
| 6 | **Run `terraform destroy`** when the VPN is not needed — avoids static IP reservation charges. |
| 7 | **Never commit `terraform.tfvars`** — it contains your SSH public key and IP allowlist. |

---

## Troubleshooting

### Check startup script log

```bash
ssh ubuntu@<vpn_public_ip>
sudo cat /var/log/openvpn-setup.log
```

### Check OpenVPN service

```bash
sudo systemctl status openvpn-server@server
sudo journalctl -u openvpn-server@server -n 50
```

### Check dnsmasq

```bash
sudo systemctl status dnsmasq
# Test DNS resolution from the server
dig @10.8.0.1 dev.hiluca.com     # should resolve to 10.128.0.12
dig @10.8.0.1 google.com          # should resolve normally
```

### Client cannot reach private VMs

- Check the VPN pool route is pushed: on the client run `ip route` (Linux) or
  check Network Preferences (macOS) and look for `10.128.0.0/20` via the VPN interface.
- Verify `net.ipv4.ip_forward=1`: `sysctl net.ipv4.ip_forward` on the server.
- Check VPC Peering is `ACTIVE` in GCP Console → VPC Network → VPC Network Peering.

### `dev.hiluca.com` not resolving when on VPN

- Verify dnsmasq is running: `sudo systemctl status dnsmasq`
- Verify Tunnelblick/OpenVPN pushed DNS: check if `10.8.0.1` appears as a DNS server in your system preferences while connected.
- Force flush DNS cache on macOS: `sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder`

### `adk.hiluca.internal` no responde (403 Forbidden)

El nginx en el servidor VPN necesita un token válido para autenticarse con Cloud Run.

```bash
ssh ubuntu@<vpn_public_ip>

# Refrescar el token manualmente
sudo /usr/local/bin/refresh-adk-token.sh

# Ver el log de refresco
sudo cat /var/log/adk-token.log

# Verificar que nginx tiene la config del token
cat /etc/nginx/conf.d/adk-token.conf
# Debe mostrar: proxy_set_header Authorization "Bearer eyJhb...";

# Verificar el nginx config
cat /etc/nginx/sites-enabled/adk-proxy
nginx -t
```

Si el token está vacío, verifica que el compute SA del servidor tenga `roles/run.invoker`:

```bash
# Desde tu Mac
SA=$(gcloud compute instances describe vpn-network-vpn \
      --zone=us-central1-a --project=careful-acumen-422922-k4 \
      --format='value(serviceAccounts[0].email)')

gcloud run services get-iam-policy hiluca-adk-dev \
  --region=us-central1 --project=careful-acumen-422922-k4
# El SA debe aparecer bajo roles/run.invoker
```

### Cloud Run sigue devolviendo 403 aunque el token es válido

Verifica que el request de nginx llega como tráfico **interno** al VPC. Esto requiere que:
1. El VPC Connector (`hiluca-adk-dev-connector`) esté `READY` en GCP Console.
2. El servidor VPN y Cloud Run estén en el mismo proyecto y VPC (`default`).

```bash
gcloud compute networks vpc-access connectors describe hiluca-adk-dev-connector \
  --region=us-central1 --project=careful-acumen-422922-k4
# state debe ser READY
```

### `allowed_admin_cidrs` – updating your IP

If your public IP changes and you can no longer SSH:

1. Use **GCP Console SSH** (works via IAP CIDR `35.235.240.0/20` which is always allowed).
2. Update `allowed_admin_cidrs` in `terraform.tfvars`.
3. Run `terraform apply` (only firewall rules update, VM is not recreated).
