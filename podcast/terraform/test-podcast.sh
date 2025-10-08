#!/bin/bash

# Test script for Cedar Mountain Podcast Infrastructure
# This script tests the RSS feed and S3 bucket functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="cedarmountainnews.todschmidt.com"
RSS_URL="https://${DOMAIN}/rss.xml"
BUCKET_NAME="cedar-mountain-podcast-dev-podcast-files"

echo -e "${BLUE}🎙️  Cedar Mountain Podcast Infrastructure Test${NC}"
echo "=================================================="
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    echo -e "${YELLOW}🔍 Checking AWS CLI configuration...${NC}"
    if aws sts get-caller-identity > /dev/null 2>&1; then
        print_status 0 "AWS CLI is configured"
        aws sts get-caller-identity --query 'Account' --output text | xargs -I {} echo "Account: {}"
    else
        print_status 1 "AWS CLI not configured or credentials expired"
        echo "Please run: aws configure or refresh your SSO credentials"
        exit 1
    fi
    echo ""
}

# Function to test RSS feed
test_rss_feed() {
    echo -e "${YELLOW}📡 Testing RSS Feed...${NC}"
    echo "RSS URL: $RSS_URL"
    echo ""
    
    # Check if RSS feed is accessible
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$RSS_URL")
    if [ "$HTTP_STATUS" = "200" ]; then
        print_status 0 "RSS feed is accessible (HTTP $HTTP_STATUS)"
        
        # Get RSS content and validate
        RSS_CONTENT=$(curl -s "$RSS_URL")
        
        if echo "$RSS_CONTENT" | grep -q "<rss"; then
            print_status 0 "RSS feed contains valid RSS structure"
        else
            print_status 1 "RSS feed does not contain valid RSS structure"
        fi
        
        if echo "$RSS_CONTENT" | grep -q "<channel>"; then
            print_status 0 "RSS feed contains channel information"
        else
            print_status 1 "RSS feed missing channel information"
        fi
        
        if echo "$RSS_CONTENT" | grep -q "<title>"; then
            print_status 0 "RSS feed contains title information"
            echo "Podcast Title: $(echo "$RSS_CONTENT" | grep -o '<title>[^<]*</title>' | head -1 | sed 's/<[^>]*>//g')"
        else
            print_status 1 "RSS feed missing title information"
        fi
        
        if echo "$RSS_CONTENT" | grep -q "<description>"; then
            print_status 0 "RSS feed contains description"
            echo "Description: $(echo "$RSS_CONTENT" | grep -o '<description>[^<]*</description>' | head -1 | sed 's/<[^>]*>//g')"
        else
            print_status 1 "RSS feed missing description"
        fi
        
        # Count episodes
        EPISODE_COUNT=$(echo "$RSS_CONTENT" | grep -c "<item>" || echo "0")
        echo "Number of episodes: $EPISODE_COUNT"
        
        if [ "$EPISODE_COUNT" -gt 0 ]; then
            print_status 0 "RSS feed contains episodes"
            echo "Sample episode titles:"
            echo "$RSS_CONTENT" | grep -o '<title>[^<]*</title>' | tail -n +2 | head -3 | sed 's/<[^>]*>//g' | sed 's/^/  - /'
        else
            print_status 1 "RSS feed contains no episodes"
            echo "Upload some MP3 files to the S3 bucket to generate episodes"
        fi
        
    else
        print_status 1 "RSS feed is not accessible (HTTP $HTTP_STATUS)"
        echo "This might be because:"
        echo "  - CloudFront distribution is still deploying"
        echo "  - SSL certificate is still validating"
        echo "  - DNS records are still propagating"
    fi
    echo ""
}

# Function to test S3 bucket
test_s3_bucket() {
    echo -e "${YELLOW}🪣 Testing S3 Bucket...${NC}"
    echo "Bucket: $BUCKET_NAME"
    echo ""
    
    # Check if bucket exists and is accessible
    if aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1; then
        print_status 0 "S3 bucket is accessible"
        
        # List bucket contents
        echo "Bucket contents:"
        aws s3 ls "s3://$BUCKET_NAME" --recursive | while read -r line; do
            echo "  $line"
        done
        
        # Count files by type
        MP3_COUNT=$(aws s3 ls "s3://$BUCKET_NAME" --recursive | grep -c "\.mp3" 2>/dev/null || echo "0")
        M4A_COUNT=$(aws s3 ls "s3://$BUCKET_NAME" --recursive | grep -c "\.m4a" 2>/dev/null || echo "0")
        RSS_COUNT=$(aws s3 ls "s3://$BUCKET_NAME" --recursive | grep -c "rss\.xml" 2>/dev/null || echo "0")
        
        echo ""
        echo "File counts:"
        echo "  MP3 files: $MP3_COUNT"
        echo "  M4A files: $M4A_COUNT"
        echo "  RSS feed: $RSS_COUNT"
        
        if [ "$RSS_COUNT" -gt 0 ]; then
            print_status 0 "RSS feed file exists in S3"
        else
            print_status 1 "RSS feed file not found in S3"
        fi
        
        if [ "$MP3_COUNT" -gt 0 ] || [ "$M4A_COUNT" -gt 0 ]; then
            print_status 0 "Audio files found in S3"
        else
            print_status 1 "No audio files found in S3"
            echo "Upload some MP3/M4A files to generate podcast episodes"
        fi
        
    else
        print_status 1 "S3 bucket is not accessible"
        echo "This might be because:"
        echo "  - Bucket doesn't exist yet"
        echo "  - Insufficient permissions"
        echo "  - Bucket name is incorrect"
    fi
    echo ""
}

# Function to test Lambda function
test_lambda_function() {
    echo -e "${YELLOW}⚡ Testing Lambda Function...${NC}"
    
    FUNCTION_NAME="cedar-mountain-podcast-dev-rss-generator"
    
    if aws lambda get-function --function-name "$FUNCTION_NAME" > /dev/null 2>&1; then
        print_status 0 "Lambda function exists"
        
        # Get function configuration
        FUNCTION_INFO=$(aws lambda get-function --function-name "$FUNCTION_NAME")
        RUNTIME=$(echo "$FUNCTION_INFO" | jq -r '.Configuration.Runtime')
        MEMORY=$(echo "$FUNCTION_INFO" | jq -r '.Configuration.MemorySize')
        TIMEOUT=$(echo "$FUNCTION_INFO" | jq -r '.Configuration.Timeout')
        
        echo "  Runtime: $RUNTIME"
        echo "  Memory: ${MEMORY}MB"
        echo "  Timeout: ${TIMEOUT}s"
        
        # Check recent invocations
        echo "Recent invocations:"
        aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/$FUNCTION_NAME" --query 'logGroups[0].logGroupName' --output text | xargs -I {} aws logs describe-log-streams --log-group-name {} --order-by LastEventTime --descending --max-items 3 --query 'logStreams[].{StreamName:logStreamName,LastEventTime:lastEventTime}' --output table 2>/dev/null || echo "  No recent invocations found"
        
    else
        print_status 1 "Lambda function not found"
    fi
    echo ""
}

# Function to show CloudFront status
test_cloudfront() {
    echo -e "${YELLOW}🌐 Testing CloudFront Distribution...${NC}"
    
    # Get distribution ID from terraform output
    DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")
    
    if [ -n "$DISTRIBUTION_ID" ]; then
        print_status 0 "CloudFront distribution found"
        echo "Distribution ID: $DISTRIBUTION_ID"
        
        # Get distribution status
        DISTRIBUTION_INFO=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID")
        STATUS=$(echo "$DISTRIBUTION_INFO" | jq -r '.Distribution.Status')
        DOMAIN_NAME=$(echo "$DISTRIBUTION_INFO" | jq -r '.Distribution.DomainName')
        
        echo "Status: $STATUS"
        echo "Domain: $DOMAIN_NAME"
        
        if [ "$STATUS" = "Deployed" ]; then
            print_status 0 "CloudFront distribution is deployed"
        else
            print_status 1 "CloudFront distribution is still deploying"
        fi
        
    else
        print_status 1 "CloudFront distribution not found in terraform state"
    fi
    echo ""
}

# Main execution
main() {
    check_aws_cli
    test_cloudfront
    test_lambda_function
    test_s3_bucket
    test_rss_feed
    
    echo -e "${BLUE}🎯 Test Summary${NC}"
    echo "================"
    echo "Domain: $DOMAIN"
    echo "RSS Feed: $RSS_URL"
    echo "S3 Bucket: $BUCKET_NAME"
    echo ""
    echo -e "${GREEN}✅ Test completed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Upload MP3 files to the S3 bucket to generate episodes"
    echo "2. Check the RSS feed URL in a browser or podcast app"
    echo "3. Submit the RSS feed to podcast platforms"
}

# Run the main function
main
