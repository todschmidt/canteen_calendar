terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
  
  # S3 backend configuration
  backend "s3" {
    # These will be provided via backend config or environment variables
    bucket = "canteen-podcast-terraform-state-1757557742"
    key    = "podcast-infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Canteen Podcast Infrastructure"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
