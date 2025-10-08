#!/bin/bash

# Script to set up S3 backend for Terraform state
# Run these commands manually since they require AWS credentials

echo "Setting up Terraform state bucket..."

# Set your preferred bucket name (must be globally unique)
STATE_BUCKET_NAME="canteen-podcast-terraform-state-$(date +%s)"

echo "Creating S3 bucket: $STATE_BUCKET_NAME"
aws s3 mb s3://$STATE_BUCKET_NAME --region us-east-1

echo "Enabling versioning on state bucket"
aws s3api put-bucket-versioning --bucket $STATE_BUCKET_NAME --versioning-configuration Status=Enabled

echo "Enabling server-side encryption on state bucket"
aws s3api put-bucket-encryption --bucket $STATE_BUCKET_NAME --server-side-encryption-configuration '{
    "Rules": [
        {
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }
    ]
}'

echo "Blocking public access on state bucket"
aws s3api put-public-access-block --bucket $STATE_BUCKET_NAME --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo ""
echo "✅ State bucket created: $STATE_BUCKET_NAME"
echo ""
echo "Now update providers.tf with these values:"
echo "bucket = \"$STATE_BUCKET_NAME\""
echo "key    = \"podcast-infrastructure/terraform.tfstate\""
echo "region = \"us-east-1\""
echo ""
echo "Or run: terraform init -backend-config=\"bucket=$STATE_BUCKET_NAME\""
