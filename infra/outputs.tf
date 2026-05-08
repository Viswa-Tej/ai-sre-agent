output "vm_external_ip" {
  description = "Public ip of the demo vm"
  value       = google_compute_instance.demo_vm.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "ready to run ssh command"
  value       = "ssh ${var.ssh_user}@${google_compute_instance.demo_vm.network_interface[0].access_config[0].nat_ip}"
}
