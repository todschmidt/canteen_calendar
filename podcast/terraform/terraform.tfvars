# Copy this file to terraform.tfvars and update the values

# AWS Configuration
aws_region = "us-east-1"
environment = "dev"

# Project Configuration
project_name = "cedar-mountain-podcast"

# Domain Configuration (optional)
# Leave empty to use CloudFront domain only
domain_name = "todschmidt.com"
subdomain = "cedarmountainnews"

# Podcast Information
podcast_title = "Canteen Calendar Podcast"
podcast_description = "Weekly podcast covering Cedar Mountain Community news"
podcast_author = "Cedar Mountain Canteer Team"
podcast_email = "tschmidty@yahoo.com"

# S3 Configuration
enable_versioning = true
enable_encryption = true

# Lambda Configuration
lambda_timeout = 30
lambda_memory_size = 128
