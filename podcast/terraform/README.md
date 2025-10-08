# Podcast Infrastructure - Terraform

This Terraform configuration sets up AWS infrastructure for hosting a podcast with automated RSS feed generation.

## Architecture

- **S3 Bucket**: Stores podcast audio files (.mp3, .m4a, etc.)
- **CloudFront**: CDN with SSL support for fast global delivery
- **ACM Certificate**: SSL certificate for custom domain (optional)
- **Lambda Function**: Automatically generates RSS feed when audio files are added/removed
- **Route53**: DNS management (if using custom domain)

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Terraform >= 1.0 installed
3. S3 bucket for Terraform state (configured in backend)

## Quick Start

1. **Configure Terraform backend**:
   ```bash
   # Create S3 bucket for Terraform state (if not exists)
   aws s3 mb s3://your-terraform-state-bucket --region us-east-1
   
   # Enable versioning on state bucket
   aws s3api put-bucket-versioning --bucket your-terraform-state-bucket --versioning-configuration Status=Enabled
   ```

2. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Initialize and apply**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Configuration

### Required Variables

- `aws_region`: AWS region for resources
- `environment`: Environment name (dev, staging, prod)
- `project_name`: Name of the project

### Optional Variables

- `domain_name`: Custom domain for the podcast
- `subdomain`: Subdomain (e.g., "media" for media.example.com)
- `podcast_title`: Title of the podcast
- `podcast_description`: Description of the podcast
- `podcast_author`: Author/owner of the podcast
- `podcast_email`: Contact email for the podcast

## Outputs

After applying, you'll get:

- `s3_bucket_name`: Name of the S3 bucket
- `cloudfront_domain_name`: CloudFront distribution domain
- `rss_feed_url`: URL of the RSS feed
- `lambda_function_name`: Name of the Lambda function

## Usage

1. **Upload audio files** to the S3 bucket
2. **RSS feed is automatically generated** when files are added/removed
3. **Access your podcast** via the CloudFront URL or custom domain
4. **Submit RSS feed URL** to podcast platforms (Apple Podcasts, Spotify, etc.)

## RSS Feed

The RSS feed is automatically generated and includes:

- Valid RSS 2.0 format
- iTunes-specific tags for Apple Podcasts compatibility
- Episode titles generated from filenames
- Publication dates based on file upload time
- HTTPS URLs for all audio files

## File Structure

```
terraform/
├── main.tf                 # Main infrastructure configuration
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── providers.tf            # Provider configuration
├── lambda.tf               # Lambda function configuration
├── lambda_function.py      # Lambda function code
├── terraform.tfvars.example # Example variables file
├── TODO.md                 # Project roadmap
└── README.md               # This file
```

## Security

- S3 bucket is private by default
- CloudFront uses Origin Access Identity (OAI) for secure access
- Lambda function has minimal required permissions
- All resources are tagged for cost tracking

## Cost Optimization

- CloudFront uses PriceClass_100 (North America and Europe)
- S3 lifecycle policies can be added for cost optimization
- Lambda function uses minimal memory allocation

## Troubleshooting

### Common Issues

1. **Certificate validation**: If using custom domain, ensure DNS validation is completed
2. **Lambda timeout**: Increase `lambda_timeout` if processing many files
3. **S3 permissions**: Ensure Lambda has proper S3 permissions

### Monitoring

- CloudWatch logs for Lambda function
- S3 access logs for file access monitoring
- CloudFront metrics for delivery performance

## Next Steps

See `TODO.md` for the complete project roadmap and enhancement ideas.
