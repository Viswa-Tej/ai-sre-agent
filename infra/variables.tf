variable "project_id" {
  description = "GCP project id "
  type        = string
}

variable "region" {
  description = " GCP region must be us-east1/us-west1/us-central1 for free tier"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "gcp zone within the free tier region"
  type        = string
  default     = "us-central1-a"
}

variable "ssh_user" {
  description = "linux username on the vm"
  type        = string
  default     = "viswa"
}

variable "public_key_path" {
  description = "path to ssh public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}
