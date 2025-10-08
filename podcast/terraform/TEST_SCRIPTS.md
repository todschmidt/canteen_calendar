# Test Scripts for Podcast Infrastructure

This directory contains test scripts to verify that the podcast infrastructure is working correctly.

## Scripts Available

### 1. `test-podcast.sh` - Comprehensive Test
A full-featured test script that checks all components of the podcast infrastructure.

**Features:**
- ✅ AWS CLI configuration check
- ✅ CloudFront distribution status
- ✅ Lambda function status and recent invocations
- ✅ S3 bucket accessibility and contents
- ✅ RSS feed validation and content analysis
- ✅ Episode counting and validation
- ✅ Color-coded output with status indicators

**Usage:**
```bash
./test-podcast.sh
```

### 2. `quick-test.sh` - Quick Test
A simplified test script for quick verification of RSS feed and S3 bucket.

**Features:**
- ✅ RSS feed accessibility check
- ✅ RSS content preview
- ✅ S3 bucket listing
- ✅ File count summary

**Usage:**
```bash
./quick-test.sh
```

## Prerequisites

Before running the test scripts, ensure:

1. **AWS CLI is configured** with appropriate permissions
2. **Terraform has been applied** and infrastructure is deployed
3. **DNS has propagated** (may take a few minutes after deployment)

## What the Scripts Test

### RSS Feed Testing
- ✅ HTTP accessibility (200 OK response)
- ✅ Valid RSS 2.0 structure
- ✅ Required RSS elements (channel, title, description)
- ✅ Episode count and content
- ✅ iTunes-specific tags

### S3 Bucket Testing
- ✅ Bucket accessibility
- ✅ File listing and counts
- ✅ Audio file detection (.mp3, .m4a)
- ✅ RSS feed file presence

### Infrastructure Testing
- ✅ CloudFront distribution status
- ✅ Lambda function configuration
- ✅ SSL certificate validation
- ✅ DNS record propagation

## Expected Results

### After Initial Deployment (No Episodes)
```
✅ RSS feed is accessible
✅ RSS feed contains valid RSS structure
✅ RSS feed contains channel information
✅ RSS feed contains title information
✅ RSS feed contains description
Number of episodes: 0
❌ RSS feed contains no episodes
```

### After Uploading Audio Files
```
✅ RSS feed is accessible
✅ RSS feed contains valid RSS structure
✅ RSS feed contains channel information
✅ RSS feed contains title information
✅ RSS feed contains description
Number of episodes: 3
✅ RSS feed contains episodes
Sample episode titles:
  - Episode 1
  - Episode 2
  - Episode 3
```

## Troubleshooting

### RSS Feed Not Accessible
- **CloudFront still deploying**: Wait 10-15 minutes
- **SSL certificate validating**: Check certificate status
- **DNS not propagated**: Wait for DNS propagation

### S3 Bucket Not Accessible
- **Bucket doesn't exist**: Run `terraform apply`
- **Insufficient permissions**: Check AWS credentials
- **Wrong bucket name**: Verify terraform.tfvars

### No Episodes in RSS Feed
- **No audio files**: Upload MP3/M4A files to S3
- **Lambda not triggered**: Check S3 event configuration
- **Lambda function error**: Check CloudWatch logs

## Manual Testing

You can also test manually:

### Test RSS Feed
```bash
curl -I https://cedarmountainnews.todschmidt.com/rss.xml
curl https://cedarmountainnews.todschmidt.com/rss.xml
```

### Test S3 Bucket
```bash
aws s3 ls s3://cedar-mountain-podcast-dev-podcast-files --recursive
```

### Test Lambda Function
```bash
aws lambda list-functions --query 'Functions[?FunctionName==`cedar-mountain-podcast-dev-rss-generator`]'
```

## Next Steps

After successful testing:

1. **Upload test audio files** to the S3 bucket
2. **Verify RSS feed updates** automatically
3. **Test RSS feed in podcast apps** (Apple Podcasts, Spotify, etc.)
4. **Submit RSS feed to podcast platforms**

## Support

If tests fail, check:
- AWS CloudWatch logs for Lambda function
- CloudFront distribution status in AWS console
- Route53 DNS records
- ACM certificate validation status
