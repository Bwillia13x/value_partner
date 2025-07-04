variable "kubeconfig_path" {
  description = "Path to kubeconfig file for cluster admin access"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace to deploy resources in"
  type        = string
  default     = "default"
}

variable "github_owner" {
  description = "GitHub owner/org used for image repo"
  type        = string
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}

variable "replica_count" {
  description = "Number of API replicas to run"
  type        = number
  default     = 2
}

variable "database_url" {
  description = "PostgreSQL connection string for the API"
  type        = string
  default     = ""
}