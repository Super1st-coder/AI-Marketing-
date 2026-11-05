# -----------------------------------------------------------------------------
# main.tf - Self-hosted OpenVPN server on Google Cloud
#
# Resources created:
#   1. VPC network          (google_compute_network)
#   2. Subnet               (google_compute_subnetwork)
#   3. Firewall - OpenVPN   (UDP openvpn_port from allowed_admin_cidrs to vpn-server)
#   4. Firewall - SSH       (TCP 22 from allowed_admin_cidrs to vpn-server)
#   5. Firewall - VPN server HTTPS egress
#   6. Firewall - VPN pool  (all protocols from 10.8.0.0/24 to private-vm)
#   7. Static external IP   (google_compute_address)
#   8. Compute Engine VM    (google_compute_instance, Ubuntu 22.04, tag: vpn-server)
# -----------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# -----------------------------------------------------------------------------
# 1. VPC Network
#    auto_create_subnetworks = false means we manage every subnet explicitly.
# -----------------------------------------------------------------------------
resource "google_compute_network" "vpn_vpc" {
  name                    = var.network_name
  auto_create_subnetworks = false
  description             = "VPC network for the OpenVPN gateway and private VMs."
}

# -----------------------------------------------------------------------------
# 2. Subnet
#    Private VMs should also live in this subnet.
#    private_ip_google_access lets VMs without public IPs reach Google APIs.
# -----------------------------------------------------------------------------
resource "google_compute_subnetwork" "vpn_subnet" {
  name                     = var.subnet_name
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpn_vpc.id
  private_ip_google_access = true
}

# -----------------------------------------------------------------------------
# 3. Firewall - OpenVPN UDP port
#    Allows inbound UDP on openvpn_port from your team's IPs.
#    Only instances tagged with vpn_tag receive this traffic.
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_openvpn" {
  name        = "${var.network_name}-allow-openvpn"
  network     = google_compute_network.vpn_vpc.name
  description = "Allow UDP/OpenVPN from admin CIDRs to the VPN gateway."

  allow {
    protocol = "udp"
    ports    = [tostring(var.openvpn_port)]
  }

  source_ranges = ["0.0.0.0/0"]   # VPN auth via certs, not IPs - safe to open
  target_tags   = [var.vpn_tag]
}

# -----------------------------------------------------------------------------
# 4. Firewall - SSH to VPN server
#    Restricted to allowed_admin_cidrs only. Never open SSH to 0.0.0.0/0.
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_ssh_vpn" {
  name        = "${var.network_name}-allow-ssh-vpn"
  network     = google_compute_network.vpn_vpc.name
  description = "Allow SSH to the VPN gateway from admin CIDRs only."

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_admin_cidrs
  target_tags   = [var.vpn_tag]
}

# -----------------------------------------------------------------------------
# 5. Firewall - VPN server HTTPS egress
#    Allows the VPN gateway VM to make outbound HTTPS connections.
#    GCP firewall rules match IP ranges, so this opens TCP/443 from the VM tag.
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_vpn_https_egress" {
  name             = "${var.network_name}-allow-vpn-https-egress"
  network          = google_compute_network.vpn_vpc.name
  description      = "Allow VPN gateway to reach HTTPS endpoints like AWS API Gateway."
  direction        = "EGRESS"
  target_tags      = [var.vpn_tag]
  destination_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}

# -----------------------------------------------------------------------------
# 6. Firewall - VPN pool to private VMs
#    Once connected, clients get an IP in 10.8.0.0/24 and can reach any
#    instance tagged with target_vm_tag via SSH, ICMP, all TCP, and all UDP.
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_vpn_to_private" {
  name        = "${var.network_name}-allow-vpn-to-private"
  network     = google_compute_network.vpn_vpc.name
  description = "Allow VPN clients (10.8.0.0/24) to reach private VMs on all ports."

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = ["10.8.0.0/24"]
  target_tags   = [var.target_vm_tag]
}

# -----------------------------------------------------------------------------
# 6. Static external IP
#    Reserved so the address never changes when the VM stops/restarts.
#    Client .ovpn files point to this IP, so stability is critical.
# -----------------------------------------------------------------------------
resource "google_compute_address" "vpn_ip" {
  name        = "${var.network_name}-vpn-ip"
  region      = var.region
  description = "Permanent external IP assigned to the OpenVPN gateway VM."
}

# -----------------------------------------------------------------------------
# 7. Compute Engine VM - OpenVPN gateway
#    Ubuntu 22.04 LTS (x86-64). The startup script below fully automates
#    OpenVPN installation, PKI setup, and NAT rules on first boot.
#
#    Fix vs original: removed EASYRSA_ALGO=ec (breaks EasyRSA 3.0.8 + OpenSSL 3.0).
#    Using RSA 2048 (default) with --batch on all easyrsa commands.
# -----------------------------------------------------------------------------
resource "google_compute_instance" "vpn_server" {
  name         = "${var.network_name}-vpn"
  machine_type = var.vpn_machine_type
  zone         = var.zone

  tags = [var.vpn_tag]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
      type  = "pd-balanced"
    }
  }

  network_interface {
    network    = google_compute_network.vpn_vpc.id
    subnetwork = google_compute_subnetwork.vpn_subnet.id

    access_config {
      nat_ip = google_compute_address.vpn_ip.address
    }
  }

  metadata = {
    ssh-keys = "ubuntu:${var.admin_ssh_pubkey}"
  }

  metadata_startup_script = <<-STARTUP
#!/usr/bin/env bash
set -euo pipefail
exec > /var/log/openvpn-setup.log 2>&1

# 0. Detect primary network interface (ens4 on GCP, eth0 elsewhere)
IFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -1)
VPN_PORT="${var.openvpn_port}"
VPN_SUBNET="10.8.0.0"
VPN_MASK="255.255.255.0"
GCP_SUBNET="${var.subnet_cidr}"

# 1. System update and package install
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
echo "iptables-persistent iptables-persistent/autosave_v4 boolean true"  | debconf-set-selections
echo "iptables-persistent iptables-persistent/autosave_v6 boolean false" | debconf-set-selections
apt-get install -y openvpn easy-rsa iptables-persistent dnsmasq

# 2. Enable IPv4 forwarding (required for NAT)
sed -i 's/^#\?\(net\.ipv4\.ip_forward\s*=\s*\).*/\11/' /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

# 2.5 Configure dnsmasq - split-horizon DNS for VPN clients
#     bind-dynamic: starts before tun0 exists, binds automatically when tun0 comes up.
#     VPN clients get 10.8.0.1 as DNS; hiluca.com subdomains resolve to the
#     private instance (10.128.0.12) which runs the existing edge-nginx with real SSL.
cat > /etc/dnsmasq.conf << 'DNSMASQ_CONF'
bind-dynamic
listen-address=10.8.0.1,127.0.0.1
no-hosts
no-resolv

# Forward unknown queries to Google DNS
server=8.8.8.8
server=8.8.4.4

# Internal overrides - all hiluca.com services on the private instance
# edge-nginx on 10.128.0.12:443 handles SSL termination and routing

# --- Frontends ---
address=/dev.hiluca.com/10.128.0.12
address=/qa.hiluca.com/10.128.0.12

# --- Sinergia API ---
address=/api-dev.hiluca.com/10.128.0.12
address=/api-qa.hiluca.com/10.128.0.12

# --- Fury (AI backend) ---
address=/fury-dev.hiluca.com/10.128.0.12

# --- n8n (workflow automation) ---
address=/n8n-dev.hiluca.com/10.128.0.12
address=/n8n-qa.hiluca.com/10.128.0.12

# --- Strapi (CMS) ---
address=/strapi-dev.hiluca.com/10.128.0.12
address=/strapi-qa.hiluca.com/10.128.0.12

# --- Langfuse (AI observability) ---
address=/langfuse-dev.hiluca.com/10.128.0.12

# --- MinIO (object storage) ---
address=/minio-dev.hiluca.com/10.128.0.12

# --- Qdrant (vector DB) ---
address=/qdrant-dev.hiluca.com/10.128.0.12

# --- ADK Cloud Run (proxied by nginx on this server) ---
# VPN clients resolve adk.hiluca.internal to this server (10.8.0.1).
# Nginx forwards the request to Cloud Run from inside the VPC.
address=/${var.adk_internal_hostname}/10.8.0.1
DNSMASQ_CONF

systemctl enable dnsmasq
systemctl restart dnsmasq

# 2.6 Configure nginx - reverse proxy for ADK Cloud Run
#     nginx receives requests for adk.hiluca.internal (from dnsmasq above)
#     and forwards them to the Cloud Run service from inside the VPC,
#     satisfying the ingress=INTERNAL_ONLY check.
#
#     SSE (Server-Sent Events) is the ADK UI transport.
#     CRITICAL settings:
#       proxy_buffering off   - prevents nginx from buffering the SSE stream
#       proxy_read_timeout    - must be >= Cloud Run timeout (3600s)
#       chunked_transfer_encoding - required for streaming
ADK_URL="${var.adk_cloud_run_url}"
if [ -n "$ADK_URL" ]; then
  apt-get install -y nginx

  cat > /etc/nginx/sites-available/adk-proxy <<NGINX_CONF
server {
    listen 80;
    server_name ${var.adk_internal_hostname};

    # Proxy all traffic to Cloud Run.
    # Cloud Run sees this request coming from the VPC (nginx VM) → INTERNAL_ONLY satisfied.
    location / {
        proxy_pass          https://$ADK_URL;
        proxy_ssl_server_name on;

        # Host header must match the Cloud Run URL for SNI + routing
        proxy_set_header    Host             \$proxy_host;
        proxy_set_header    X-Real-IP        \$remote_addr;
        proxy_set_header    X-Forwarded-For  \$proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto http;

        # ── SSE (Server-Sent Events) support ──────────────────────────────
        # ADK web UI streams responses over SSE. These settings are required.
        proxy_http_version 1.1;
        proxy_set_header   Connection        '';
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 3600s;           # Match Cloud Run's max timeout
        proxy_send_timeout 3600s;
        chunked_transfer_encoding on;
    }
}
NGINX_CONF

  # Enable site and disable default
  ln -sf /etc/nginx/sites-available/adk-proxy /etc/nginx/sites-enabled/adk-proxy
  rm -f /etc/nginx/sites-enabled/default

  nginx -t && systemctl enable nginx && systemctl restart nginx
  echo "[ADK proxy] nginx configured for $ADK_URL → ${var.adk_internal_hostname}"
else
  echo "[ADK proxy] adk_cloud_run_url is empty, skipping nginx proxy setup."
fi

# 3. Build PKI with EasyRSA
#    RSA 2048 (default) - fully compatible with EasyRSA 3.0.8 + OpenSSL 3.0.
#    --batch avoids all interactive prompts.
make-cadir /etc/openvpn/easy-rsa
cd /etc/openvpn/easy-rsa

./easyrsa init-pki
echo "HiLuca-CA" | ./easyrsa --batch build-ca nopass
./easyrsa --batch gen-req server nopass
echo "yes" | ./easyrsa --batch sign-req server server

# TLS-auth key: extra HMAC layer, blocks unauthenticated UDP (anti-DoS)
openvpn --genkey secret /etc/openvpn/ta.key

# Copy server material
install -d -m 700 /etc/openvpn/server
install -m 600 pki/ca.crt             /etc/openvpn/server/
install -m 600 pki/issued/server.crt  /etc/openvpn/server/
install -m 600 pki/private/server.key /etc/openvpn/server/
cp /etc/openvpn/ta.key                /etc/openvpn/server/

# 4. Write OpenVPN server.conf
#    dh none is valid in OpenVPN 2.5+ with RSA certs (ECDHE handles PFS).
cat > /etc/openvpn/server/server.conf << OVPN_CONF
port $VPN_PORT
proto udp
dev tun

ca   /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key  /etc/openvpn/server/server.key

tls-auth /etc/openvpn/server/ta.key 0

dh none

server $VPN_SUBNET $VPN_MASK

max-clients 100

duplicate-cn

push "route $GCP_SUBNET"
push "route 10.128.0.0 255.255.240.0"
push "redirect-gateway def1"
push "dhcp-option DNS 10.8.0.1"

keepalive 10 120
tls-version-min 1.2
data-ciphers AES-256-GCM:AES-128-GCM
auth SHA256

user nobody
group nogroup

persist-key
persist-tun
mssfix 1280
replay-window 128 30

status     /var/log/openvpn-status.log
log-append /var/log/openvpn.log
verb 3

OVPN_CONF

# 5. iptables NAT
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o "$IFACE" -j MASQUERADE
iptables -A FORWARD -i tun0 -j ACCEPT
iptables -A FORWARD -o tun0 -j ACCEPT
netfilter-persistent save

# 6. Enable and start OpenVPN
systemctl enable  openvpn-server@server
systemctl restart openvpn-server@server

# 7. Write the make-client-ovpn.sh helper
#    Usage: sudo bash /root/make-client-ovpn.sh <client-name>
cat > /root/make-client-ovpn.sh << 'MAKE_OVPN'
#!/usr/bin/env bash
set -euo pipefail
CLIENT="$${1:?Usage: $0 <client-name> [days-valid]}"
VPN_IP=$(curl -s https://ifconfig.me)
VPN_PORT="1194"
EASY_RSA_DIR="/etc/openvpn/easy-rsa"
OUT="/root/$${CLIENT}.ovpn"
# Generate client cert if it doesn't already exist
# Optional second arg: expiration in days (default 365)
DAYS="$${2:-365}"
if [ ! -f "$EASY_RSA_DIR/pki/issued/$${CLIENT}.crt" ]; then
  echo "Generating certificate for $${CLIENT} (expires in $${DAYS} days)..."
  cd "$EASY_RSA_DIR"
  ./easyrsa --batch gen-req "$${CLIENT}" nopass
  EASYRSA_CERT_EXPIRE="$${DAYS}" ./easyrsa --batch sign-req client "$${CLIENT}"
else
  echo "Certificate for $${CLIENT} already exists, skipping generation."
fi
cat > "$OUT" << OVPN
client
dev tun
proto udp
remote $VPN_IP $VPN_PORT
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
tls-version-min 1.2
data-ciphers AES-256-GCM:AES-128-GCM
auth SHA256
verb 3
key-direction 1
mssfix 1280
replay-window 128 30
<ca>
$(cat $EASY_RSA_DIR/pki/ca.crt)
</ca>
<cert>
$(openssl x509 -in $EASY_RSA_DIR/pki/issued/$${CLIENT}.crt)
</cert>
<key>
$(cat $EASY_RSA_DIR/pki/private/$${CLIENT}.key)
</key>
<tls-auth>
$(cat /etc/openvpn/ta.key)
</tls-auth>
OVPN
chmod 600 "$OUT"
echo "Done! Client profile: $OUT"
echo "Download with: scp ubuntu@$VPN_IP:/root/$${CLIENT}.ovpn ."
MAKE_OVPN
chmod +x /root/make-client-ovpn.sh

echo "=== OpenVPN setup complete at $(date) ===" >> /var/log/openvpn-setup.log
STARTUP

  service_account {
    scopes = ["cloud-platform"]
  }

  depends_on = [
    google_compute_address.vpn_ip,
    google_compute_subnetwork.vpn_subnet,
  ]
}

# =============================================================================
# VPC Peering - vpn-network ↔ default VPC (10.128.0.0/20)
# Your instance at 10.128.0.12 lives here.
# =============================================================================
resource "google_compute_network_peering" "vpn_to_default" {
  name         = "vpn-to-default"
  network      = google_compute_network.vpn_vpc.self_link
  peer_network = "projects/${var.project_id}/global/networks/default"
}

resource "google_compute_network_peering" "default_to_vpn" {
  name         = "default-to-vpn"
  network      = "projects/${var.project_id}/global/networks/default"
  peer_network = google_compute_network.vpn_vpc.self_link
  depends_on   = [google_compute_network_peering.vpn_to_default]
}

resource "google_compute_firewall" "allow_vpn_to_default" {
  name          = "allow-vpn-clients-to-default"
  network       = "default"
  description   = "Allow VPN clients (10.8.0.0/24) to reach instances in default VPC."

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = [
    "10.8.0.0/24",    # VPN client pool
    "10.10.0.0/24",   # VPN server NIC (actual source after NAT masquerade)
  ]
}

# NOTE: hlc-lbu-dev-vpc peering is NOT possible.
# Both hlc-lbu-dev-vpc and default VPC share a 10.8.0.0/28 VPC connector subnet,
# which conflicts with the OpenVPN pool (10.8.0.0/24) when both are peered.
# The default VPC peering above covers the primary use case.
