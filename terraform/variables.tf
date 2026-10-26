variable "kubeconfig_path" {
  description = "Path to the kubeconfig for the local Kubernetes cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Optional kubeconfig context; empty uses the current context."
  type        = string
  default     = ""
}

variable "storage_node_name" {
  description = "Kubernetes node hostname that holds local hostPath volumes."
  type        = string
  default     = "lamu-tours-control-plane"
}

variable "namespace" {
  description = "Namespace for the application and its supporting services."
  type        = string
  default     = "lamu-tours"
}

variable "app_image" {
  description = "Application image already available to the selected local cluster."
  type        = string
  default     = "lamu-tours:local"
}

variable "image_pull_policy" {
  description = "Kubernetes image pull policy; use IfNotPresent for local images."
  type        = string
  default     = "IfNotPresent"
}

variable "app_replicas" {
  description = "Number of application pods."
  type        = number
  default     = 1

  validation {
    condition     = var.app_replicas >= 1 && floor(var.app_replicas) == var.app_replicas
    error_message = "app_replicas must be a positive whole number."
  }
}

variable "site_url" {
  description = "Public site URL. Use HTTPS when exposing the app outside local development."
  type        = string
  default     = "http://localhost:8080"
}

variable "secret_key" {
  description = "Persistent Flask session signing secret."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.secret_key) >= 32
    error_message = "secret_key must contain at least 32 characters."
  }
}

variable "postgres_password" {
  description = "Password for the PostgreSQL application user."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.postgres_password) >= 16
    error_message = "postgres_password must contain at least 16 characters."
  }
}

variable "daraja_environment" {
  description = "Daraja API environment: sandbox for testing or production for live payments."
  type        = string
  default     = "sandbox"

  validation {
    condition     = contains(["sandbox", "production"], var.daraja_environment)
    error_message = "daraja_environment must be sandbox or production."
  }
}

variable "daraja_callback_url" {
  description = "Public HTTPS URL that Daraja calls with STK Push results."
  type        = string
  default     = "https://lamutours.co.ke/daraja/callback"
}

variable "daraja_consumer_key" {
  description = "Daraja API consumer key."
  type        = string
  sensitive   = true
  default     = ""
}

variable "daraja_consumer_secret" {
  description = "Daraja API consumer secret."
  type        = string
  sensitive   = true
  default     = ""
}

variable "daraja_shortcode" {
  description = "M-Pesa business shortcode for STK Push."
  type        = string
  sensitive   = true
  default     = ""
}

variable "daraja_passkey" {
  description = "Lipa Na M-Pesa Online passkey."
  type        = string
  sensitive   = true
  default     = ""
}

variable "email_host" {
  description = "Optional SMTP server hostname."
  type        = string
  default     = ""
}

variable "email_port" {
  description = "SMTP server port."
  type        = number
  default     = 587
}

variable "email_username" {
  description = "Optional SMTP username."
  type        = string
  sensitive   = true
  default     = ""
}

variable "email_password" {
  description = "Optional SMTP password."
  type        = string
  sensitive   = true
  default     = ""
}

variable "email_from" {
  description = "Optional sender address for email."
  type        = string
  default     = ""
}

variable "email_to" {
  description = "Recipient address for contact notifications."
  type        = string
  default     = "info@lamutours.com"
}

variable "admin_email" {
  description = "Optional initial administrator email; used only when bootstrapping an empty database."
  type        = string
  default     = ""
}

variable "admin_password" {
  description = "Optional initial administrator password; used only when bootstrapping an empty database."
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_name" {
  description = "Name used for the initial administrator account."
  type        = string
  default     = "Administrator"
}

variable "postgres_storage" {
  description = "Requested local persistent volume capacity for PostgreSQL data."
  type        = string
  default     = "5Gi"
}

variable "uploads_storage" {
  description = "Requested local persistent volume capacity for uploaded catalog images."
  type        = string
  default     = "2Gi"
}
