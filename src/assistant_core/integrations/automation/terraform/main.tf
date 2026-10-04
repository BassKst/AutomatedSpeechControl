terraform {
  required_providers {
    hcloud = {
      source = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "default" {
  name       = "vpn-automation-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

resource "hcloud_server" "vpn_node" {

  name = var.node_name

  image       = "ubuntu-22.04"
  server_type = "cx22"
  location    = var.region

  ssh_keys = [
    hcloud_ssh_key.default.id
  ]

  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }
}