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
podcast_title = "Cedar Mountain Community News Podcast"
podcast_description = "Weekly podcast covering Cedar Mountain, NC Community news"
podcast_author = "Cedar Mountain Canteen Team"
podcast_email = "tschmidty@yahoo.com"
artwork_url="https://cedarmountainnews.todschmidt.com/Cedar_Mountain_Community_News_Podcast.jpg"
podcast_category = "News"
podcast_category_subcategory = "Local"

# S3 Configuration
enable_versioning = true
enable_encryption = true

# Lambda Configuration
lambda_timeout = 30
lambda_memory_size = 128
