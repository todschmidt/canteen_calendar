variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g. prod)"
  type        = string
  default     = "prod"
}

variable "zone_id" {
  description = "Route53 hosted zone ID (e.g. Z2HGXTW05Q9PAJ)"
  type        = string
}

variable "record_name" {
  description = "DNS record name (single label, e.g. home)"
  type        = string
  default     = "home"
}

variable "api_key" {
  description = "API key required in GET requests (store in terraform.tfvars, do not commit)"
  type        = string
  sensitive   = true
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 10
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 128
}
