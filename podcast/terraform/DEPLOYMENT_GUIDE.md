# Deployment Guide - Podcast Infrastructure

## Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed
- AWS credentials available (SSO or IAM)

## Step 1: Create Terraform State Bucket

**Option A: Use the setup script**
```bash
chmod +x setup-backend.sh
./setup-backend.sh
```

**Option B: Manual commands**
```bash
# Create a unique bucket name
STATE_BUCKET="canteen-podcast-terraform-state-$(date +%s)"

# Create the bucket
aws s3 mb s3://$STATE_BUCKET --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning --bucket $STATE_BUCKET --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption --bucket $STATE_BUCKET --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
}'

# Block public access
aws s3api put-public-access-block --bucket $STATE_BUCKET --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "Bucket created: $STATE_BUCKET"
```

## Step 2: Configure Terraform Backend

**Option A: Update providers.tf directly**
Uncomment and fill in the backend configuration in `providers.tf`:
```hcl
backend "s3" {
  bucket = "your-actual-bucket-name"
  key    = "podcast-infrastructure/terraform.tfstate"
  region = "us-east-1"
}
```

**Option B: Use backend config file**
```bash
# Create backend-config.tfvars with your bucket name
echo 'bucket = "your-actual-bucket-name"' > backend-config.tfvars
echo 'key    = "podcast-infrastructure/terraform.tfstate"' >> backend-config.tfvars
echo 'region = "us-east-1"' >> backend-config.tfvars
```

## Step 3: Configure Variables

```bash
# Copy and edit the variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values:
# - domain_name (optional, for custom domain)
# - podcast_title, podcast_description, etc.
```

## Step 4: Initialize Terraform

**If you updated providers.tf:**
```bash
terraform init
```

**If using backend config file:**
```bash
terraform init -backend-config=backend-config.tfvars
```

## Step 5: Plan and Apply

```bash
# Review the plan
terraform plan

# Apply the infrastructure
terraform apply
```

## Step 6: Verify Deployment

After successful deployment, you'll get outputs like:
- `s3_bucket_name`: Your podcast files bucket
- `cloudfront_domain_name`: CloudFront distribution URL
- `rss_feed_url`: Your podcast RSS feed URL

## Step 7: Test the Setup

1. Upload a test MP3 file to the S3 bucket
2. Check that the RSS feed is generated automatically
3. Verify the RSS feed URL is accessible via HTTPS

## Troubleshooting

### Common Issues:
1. **Bucket already exists**: Choose a different bucket name
2. **Permission denied**: Ensure AWS credentials have S3, CloudFront, Lambda, ACM permissions
3. **Certificate validation**: If using custom domain, complete DNS validation

### Useful Commands:
```bash
# Check Terraform state
terraform show

# List resources
terraform state list

# Destroy infrastructure (if needed)
terraform destroy
```

## Next Steps

1. Upload your first podcast episode to the S3 bucket
2. Submit your RSS feed URL to podcast platforms:
   - Apple Podcasts
   - Spotify for Podcasters
   - Google Podcasts
3. Monitor CloudWatch logs for Lambda function
4. Set up cost alerts in AWS Billing
