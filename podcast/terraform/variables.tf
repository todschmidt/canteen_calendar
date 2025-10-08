variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "podcast"
}

variable "domain_name" {
  description = "Domain name for the podcast (optional)"
  type        = string
  default     = ""
}

variable "subdomain" {
  description = "Subdomain for the podcast media (e.g., media)"
  type        = string
  default     = "media"
}

variable "podcast_title" {
  description = "Title of the podcast"
  type        = string
  default     = "Canteen Calendar Podcast"
}

variable "podcast_description" {
  description = "Description of the podcast"
  type        = string
  default     = "Weekly podcast covering canteen events and community news"
}

variable "podcast_author" {
  description = "Author/owner of the podcast"
  type        = string
  default     = "Canteen Calendar Team"
}

variable "podcast_email" {
  description = "Contact email for the podcast"
  type        = string
  default     = "podcast@example.com"
}

variable "enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable S3 bucket encryption"
  type        = bool
  default     = true
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 128
}
