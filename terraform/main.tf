locals {
  app_labels = {
    app = "lamu-tours"
  }
  postgres_labels = {
    app = "lamu-postgres"
  }
  redis_labels = {
    app = "lamu-redis"
  }
}

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_config_map_v1" "app" {
  metadata {
    name      = "lamu-tours-config"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  data = {
    PORT                  = "5000"
    SITE_URL              = var.site_url
    DARAJA_ENV            = var.daraja_environment
    DARAJA_CALLBACK_URL   = var.daraja_callback_url
    RATELIMIT_STORAGE_URI = "redis://redis:6379/0"
    FLASK_DEBUG           = "false"
    EMAIL_HOST            = var.email_host
    EMAIL_PORT            = tostring(var.email_port)
    EMAIL_FROM            = var.email_from
    EMAIL_TO              = var.email_to
    EMAIL_USE_TLS         = "true"
    EMAIL_USE_SSL         = "false"
    ADMIN_EMAIL           = var.admin_email
    ADMIN_NAME            = var.admin_name
  }
}

resource "kubernetes_secret_v1" "app" {
  metadata {
    name      = "lamu-tours-secrets"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  type = "Opaque"

  data = {
    SECRET_KEY            = var.secret_key
    POSTGRES_PASSWORD     = var.postgres_password
    DATABASE_URL          = "postgresql+psycopg://lamu_tours:${replace(urlencode(var.postgres_password), "+", "%20")}@postgres:5432/lamu_tours"
    DARAJA_CONSUMER_KEY    = var.daraja_consumer_key
    DARAJA_CONSUMER_SECRET = var.daraja_consumer_secret
    DARAJA_SHORTCODE       = var.daraja_shortcode
    DARAJA_PASSKEY         = var.daraja_passkey
    EMAIL_USERNAME        = var.email_username
    EMAIL_PASSWORD        = var.email_password
    ADMIN_PASSWORD        = var.admin_password
  }
}

resource "kubernetes_persistent_volume_v1" "postgres" {
  metadata {
    name = "lamu-postgres-data"
  }

  spec {
    capacity = {
      storage = var.postgres_storage
    }
    access_modes                     = ["ReadWriteOnce"]
    persistent_volume_reclaim_policy = "Retain"
    storage_class_name               = ""

    persistent_volume_source {
      host_path {
        path = "/var/local-path-provisioner/lamu-tours/postgres"
        type = "DirectoryOrCreate"
      }
    }

    node_affinity {
      required {
        node_selector_term {
          match_expressions {
            key      = "kubernetes.io/hostname"
            operator = "In"
            values   = [var.storage_node_name]
          }
        }
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "postgres" {
  metadata {
    name      = "postgres-data"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = ""
    volume_name        = kubernetes_persistent_volume_v1.postgres.metadata[0].name

    resources {
      requests = {
        storage = var.postgres_storage
      }
    }
  }
}

resource "kubernetes_stateful_set_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    service_name = "postgres"
    replicas     = 1

    selector {
      match_labels = local.postgres_labels
    }

    template {
      metadata {
        labels = local.postgres_labels
      }

      spec {
        container {
          name              = "postgres"
          image             = "postgres:16-alpine"
          image_pull_policy = "IfNotPresent"

          port {
            name           = "postgres"
            container_port = 5432
          }

          env {
            name  = "POSTGRES_DB"
            value = "lamu_tours"
          }

          env {
            name  = "POSTGRES_USER"
            value = "lamu_tours"
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.app.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }

          volume_mount {
            name       = "postgres-data"
            mount_path = "/var/lib/postgresql/data"
            sub_path   = "postgres"
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "lamu_tours", "-d", "lamu_tours"]
            }

            initial_delay_seconds = 5
            period_seconds        = 5
          }

          liveness_probe {
            exec {
              command = ["pg_isready", "-U", "lamu_tours", "-d", "lamu_tours"]
            }

            initial_delay_seconds = 30
            period_seconds        = 10
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }
        }

        volume {
          name = "postgres-data"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.postgres.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    selector = local.postgres_labels

    port {
      name        = "postgres"
      port        = 5432
      target_port = "postgres"
    }
  }
}

resource "kubernetes_deployment_v1" "redis" {
  metadata {
    name      = "redis"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = local.redis_labels
    }

    template {
      metadata {
        labels = local.redis_labels
      }

      spec {
        container {
          name              = "redis"
          image             = "redis:7.4-alpine"
          image_pull_policy = "IfNotPresent"

          port {
            name           = "redis"
            container_port = 6379
          }

          readiness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }

            initial_delay_seconds = 5
            period_seconds        = 5
          }

          liveness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }

            initial_delay_seconds = 15
            period_seconds        = 10
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              cpu    = "250m"
              memory = "256Mi"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "redis" {
  metadata {
    name      = "redis"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    selector = local.redis_labels

    port {
      name        = "redis"
      port        = 6379
      target_port = "redis"
    }
  }
}

resource "kubernetes_persistent_volume_v1" "uploads" {
  metadata {
    name = "lamu-uploads-data"
  }

  spec {
    capacity = {
      storage = var.uploads_storage
    }
    access_modes                     = ["ReadWriteOnce"]
    persistent_volume_reclaim_policy = "Retain"
    storage_class_name               = ""

    persistent_volume_source {
      host_path {
        path = "/var/local-path-provisioner/lamu-tours/uploads"
        type = "DirectoryOrCreate"
      }
    }

    node_affinity {
      required {
        node_selector_term {
          match_expressions {
            key      = "kubernetes.io/hostname"
            operator = "In"
            values   = [var.storage_node_name]
          }
        }
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "uploads" {
  metadata {
    name      = "uploads"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = ""
    volume_name        = kubernetes_persistent_volume_v1.uploads.metadata[0].name

    resources {
      requests = {
        storage = var.uploads_storage
      }
    }
  }
}

resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "lamu-tours"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    replicas = var.app_replicas

    selector {
      match_labels = local.app_labels
    }

    template {
      metadata {
        labels = local.app_labels
      }

      spec {
        security_context {
          run_as_non_root = true
          run_as_user     = 10001
          run_as_group    = 10001
          fs_group        = 10001
        }

        init_container {
          name    = "prepare-uploads"
          image   = "busybox:1.36"
          command = ["sh", "-c", "mkdir -p /uploads && chown 10001:10001 /uploads && chmod 0775 /uploads"]

          security_context {
            run_as_non_root = false
            run_as_user     = 0
          }

          volume_mount {
            name       = "uploads"
            mount_path = "/uploads"
          }
        }

        init_container {
          name    = "wait-for-postgres"
          image   = "postgres:16-alpine"
          command = ["sh", "-c", "until pg_isready -h postgres -p 5432 -U lamu_tours; do sleep 2; done"]
        }

        container {
          name              = "app"
          image             = var.app_image
          image_pull_policy = var.image_pull_policy

          port {
            name           = "http"
            container_port = 5000
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map_v1.app.metadata[0].name
            }
          }

          env_from {
            secret_ref {
              name = kubernetes_secret_v1.app.metadata[0].name
            }
          }

          volume_mount {
            name       = "uploads"
            mount_path = "/app/uploads"
          }

          readiness_probe {
            http_get {
              path = "/readyz"
              port = "http"
            }

            initial_delay_seconds = 10
            period_seconds        = 10
          }

          liveness_probe {
            http_get {
              path = "/healthz"
              port = "http"
            }

            initial_delay_seconds = 30
            period_seconds        = 20
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "768Mi"
            }
          }
        }

        volume {
          name = "uploads"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.uploads.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "lamu-tours"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    selector = local.app_labels

    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
