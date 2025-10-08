# Data sources
data "aws_caller_identity" "current" {}

# S3 Bucket for podcast files
resource "aws_s3_bucket" "podcast_bucket" {
  bucket = "${var.project_name}-${var.environment}-podcast-files"

  tags = {
    Name        = "${var.project_name}-${var.environment}-podcast-files"
    Environment = var.environment
    Purpose     = "Podcast audio file storage"
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "podcast_bucket_versioning" {
  count  = var.enable_versioning ? 1 : 0
  bucket = aws_s3_bucket.podcast_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "podcast_bucket_encryption" {
  count  = var.enable_encryption ? 1 : 0
  bucket = aws_s3_bucket.podcast_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "podcast_bucket_pab" {
  bucket = aws_s3_bucket.podcast_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket logging
resource "aws_s3_bucket_logging" "podcast_bucket_logging" {
  bucket = aws_s3_bucket.podcast_bucket.id

  target_bucket = aws_s3_bucket.podcast_bucket.id
  target_prefix = "logs/"
}

# Origin Access Identity for CloudFront
resource "aws_cloudfront_origin_access_identity" "podcast_oai" {
  comment = "OAI for ${var.project_name}-${var.environment} podcast bucket"
}

# S3 Bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "podcast_bucket_policy" {
  bucket = aws_s3_bucket.podcast_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOriginAccessIdentity"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.podcast_oai.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.podcast_bucket.arn}/*"
      }
    ]
  })

  depends_on = [aws_cloudfront_origin_access_identity.podcast_oai]
}

# ACM Certificate (only if domain is provided)
resource "aws_acm_certificate" "podcast_cert" {
  count = var.domain_name != "" ? 1 : 0

  domain_name       = "${var.subdomain}.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-cert"
  }
}

# Wait for certificate validation
resource "aws_acm_certificate_validation" "podcast_cert_validation" {
  count = var.domain_name != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.podcast_cert[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  timeouts {
    create = "10m"
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "podcast_distribution" {
  origin {
    domain_name = aws_s3_bucket.podcast_bucket.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.podcast_bucket.bucket}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.podcast_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name}-${var.environment} podcast distribution"
  default_root_object = "index.html"

  # Custom domain configuration (if domain is provided)
  aliases = var.domain_name != "" ? ["${var.subdomain}.${var.domain_name}"] : []

  # SSL certificate configuration
  dynamic "viewer_certificate" {
    for_each = var.domain_name != "" ? [1] : []
    content {
      acm_certificate_arn      = aws_acm_certificate_validation.podcast_cert_validation[0].certificate_arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }

  dynamic "viewer_certificate" {
    for_each = var.domain_name == "" ? [1] : []
    content {
      cloudfront_default_certificate = true
    }
  }

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.podcast_bucket.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Cache behavior for audio files
  ordered_cache_behavior {
    path_pattern           = "*.mp3"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.podcast_bucket.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  # Cache behavior for RSS feed
  ordered_cache_behavior {
    path_pattern           = "rss.xml"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.podcast_bucket.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 300
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-distribution"
    Environment = var.environment
  }
}

# Upload test player HTML file to S3
resource "aws_s3_object" "test_player" {
  bucket = aws_s3_bucket.podcast_bucket.id
  key    = "test-player.html"
  source = "${path.module}/test-player.html"
  etag   = filemd5("${path.module}/test-player.html")
  content_type = "text/html"

  tags = {
    Name        = "${var.project_name}-${var.environment}-test-player"
    Environment = var.environment
    Purpose     = "Podcast test player"
  }
}
