# -----------------------------------------------------------------------------
# outputs.tf - Values printed after terraform apply
# -----------------------------------------------------------------------------

# Public IP of the OpenVPN gateway (goes into every client .ovpn file).
output "vpn_public_ip" {
  description = "Static external IPv4 address of the OpenVPN server."
  value       = google_compute_address.vpn_ip.address
}

# Ready-to-paste SSH command for admins.
output "ssh_command" {
  description = "SSH command to log into the OpenVPN gateway as 'ubuntu'."
  value       = "ssh ubuntu@${google_compute_address.vpn_ip.address}"
}

# Human-readable post-deployment checklist.
output "next_steps" {
  description = "What to do after apply to generate client certificates and .ovpn files."
  value       = <<-EOT
    ---------------------------------------------------------
    OpenVPN server deployed! Next steps:
    ---------------------------------------------------------

    1. SSH into the server:
         ssh ubuntu@${google_compute_address.vpn_ip.address}

    2. Wait for the startup script to finish (~3-5 min):
         sudo journalctl -u openvpn-server@server -f
         # or: sudo cat /var/log/openvpn-setup.log

    3. Create a client certificate for each team member:
         cd /etc/openvpn/easy-rsa
         sudo ./easyrsa gen-req alice nopass
         echo "yes" | sudo ./easyrsa sign-req client alice

    4. Build the .ovpn bundle:
         sudo bash /root/make-client-ovpn.sh alice
         # (see README.md for the make-client-ovpn.sh script)

    5. Securely transfer the .ovpn file to the team member:
         scp ubuntu@${google_compute_address.vpn_ip.address}:~/alice.ovpn .

    6. Import and connect (see README.md for macOS / Windows / Linux).
    ---------------------------------------------------------
  EOT
}
