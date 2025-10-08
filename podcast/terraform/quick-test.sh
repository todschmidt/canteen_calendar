#!/bin/bash

# Quick test script for podcast infrastructure
# Tests RSS feed and S3 bucket listing

set -e

# Configuration
DOMAIN="cedarmountainnews.todschmidt.com"
RSS_URL="https://${DOMAIN}/rss.xml"
BUCKET_NAME="cedar-mountain-podcast-dev-podcast-files"

echo "🎙️  Quick Podcast Test"
echo "====================="
echo ""

# Test RSS Feed
echo "📡 Testing RSS Feed: $RSS_URL"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$RSS_URL")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ RSS feed is accessible (HTTP $HTTP_STATUS)"
    
    # Show RSS content
    echo ""
    echo "RSS Feed Content:"
    echo "----------------"
    curl -s "$RSS_URL" | head -20
    echo ""
    
    # Count episodes
    EPISODE_COUNT=$(curl -s "$RSS_URL" | grep -c "<item>" || echo "0")
    echo "Number of episodes: $EPISODE_COUNT"
    
else
    echo "❌ RSS feed is not accessible (HTTP $HTTP_STATUS)"
    echo "This might be because:"
    echo "  - CloudFront distribution is still deploying"
    echo "  - SSL certificate is still validating"
    echo "  - DNS records are still propagating"
fi

echo ""

# Test S3 Bucket
echo "🪣 Testing S3 Bucket: $BUCKET_NAME"
if aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1; then
    echo "✅ S3 bucket is accessible"
    echo ""
    echo "Bucket Contents:"
    echo "---------------"
    aws s3 ls "s3://$BUCKET_NAME" --recursive
    
    # Count files
    MP3_COUNT=$(aws s3 ls "s3://$BUCKET_NAME" --recursive | grep -c "\.mp3" 2>/dev/null || echo "0")
    RSS_COUNT=$(aws s3 ls "s3://$BUCKET_NAME" --recursive | grep -c "rss\.xml" 2>/dev/null || echo "0")
    
    echo ""
    echo "File counts:"
    echo "  MP3 files: $MP3_COUNT"
    echo "  RSS feed: $RSS_COUNT"
    
else
    echo "❌ S3 bucket is not accessible"
fi

echo ""
echo "🎯 Quick test completed!"
