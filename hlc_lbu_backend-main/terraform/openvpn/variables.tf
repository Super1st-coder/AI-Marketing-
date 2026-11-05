# -----------------------------------------------------------------------------
# variables.tf - Input variable declarations for the OpenVPN Terraform module
# -----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID where all resources will be created."
  type        = string
}

variable "region" {
  description = "GCP region (e.g. us-central1)."
  type        = string
}

variable "zone" {
  description = "GCP zone for the VPN VM (e.g. us-central1-a)."
  type        = string
}

variable "network_name" {
  description = "Name of the VPC network to create."
  type        = string
}

variable "subnet_name" {
  description = "Name of the subnet to create inside the VPC."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet (e.g. 10.10.0.0/24)."
  type        = string
}

variable "vpn_machine_type" {
  description = "GCP machine type for the OpenVPN VM."
  type        = string
  default     = "e2-micro"
}

variable "admin_ssh_pubkey" {
  description = "SSH public key injected for the 'ubuntu' user on the VPN VM."
  type        = string
}

variable "allowed_admin_cidrs" {
  description = <<-EOT
    List of CIDR ranges allowed to:
      - Open a VPN connection (UDP openvpn_port)
      - SSH into the VPN server (TCP 22)
    Use your team's static egress IPs. Avoid 0.0.0.0/0 for SSH.
  EOT
  type        = list(string)
}

variable "target_vm_tag" {
  description = "Network tag applied to private VMs that VPN clients should reach."
  type        = string
  default     = "private-vm"
}

variable "vpn_tag" {
  description = "Network tag applied to the OpenVPN gateway VM."
  type        = string
  default     = "vpn-server"
}

variable "openvpn_port" {
  description = "UDP port OpenVPN listens on."
  type        = number
  default     = 1194
}

# -----------------------------------------------------------------------------
# ADK Cloud Run reverse proxy
# -----------------------------------------------------------------------------

variable "adk_cloud_run_url" {
  description = <<-EOT
    Hostname del servicio ADK en Cloud Run (sin https://).
    Obtenlo del output cloud_run_hostname del módulo adk.
    Ejemplo: hiluca-adk-dev-bvuoyah6iq-uc.a.run.app
    Nginx usará este valor como proxy_pass backend.
    Deja vacío ("") para omitir la configuración del proxy.
  EOT
  type        = string
  default     = ""
}

variable "adk_internal_hostname" {
  description = <<-EOT
    Hostname interno que dnsmasq resuelve para los clientes VPN.
    Los clientes accederán al ADK usando este nombre en el browser.
    Debe terminar en .internal u otro dominio no-público.
  EOT
  type        = string
  default     = "adk.hiluca.internal"
}
