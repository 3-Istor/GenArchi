terraform {
  required_version = ">= 1.11"
  required_providers {
    google     = { source = "hashicorp/google", version = "~> 8.8" }
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 5.27" }
    random     = { source = "hashicorp/random", version = "~> 3.7" }
  }
  backend "gcs" {
    prefix = "genarchi/p2"
  }
}
