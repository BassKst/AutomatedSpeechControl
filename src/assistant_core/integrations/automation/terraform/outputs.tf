output "server_ip" {
  value = hcloud_server.vpn_node.ipv4_address
}

output "ssh_user" {
  value = "root"
}