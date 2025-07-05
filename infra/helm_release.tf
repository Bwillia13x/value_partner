# Helm release to deploy the FastAPI workload using the in-repo chart

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

resource "helm_release" "api" {
  name       = "valueinvest-api"
  namespace  = var.namespace
  chart      = "${path.module}/helm/value-investing-api"
  dependency_update = true

  set {
    name  = "image.repository"
    value = "ghcr.io/${var.github_owner}/value-investing-api"
  }
  set {
    name  = "image.tag"
    value = var.image_tag
  }
  set {
    name  = "env.DATABASE_URL"
    value = var.database_url
  }

  values = [
    yamlencode({
      replicaCount = var.replica_count
    })
  ]
}