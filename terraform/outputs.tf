output "namespace" {
  description = "Kubernetes namespace containing the application."
  value       = kubernetes_namespace_v1.app.metadata[0].name
}

output "service_name" {
  description = "ClusterIP service name for the application."
  value       = kubernetes_service_v1.app.metadata[0].name
}

output "port_forward_command" {
  description = "Command to access the app locally."
  value       = "kubectl port-forward service/${kubernetes_service_v1.app.metadata[0].name} 8080:80 -n ${kubernetes_namespace_v1.app.metadata[0].name}"
}
