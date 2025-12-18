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

# Origin Access Control for CloudFront (replaces deprecated OAI)
resource "aws_cloudfront_origin_access_control" "podcast_oac" {
  name                              = "${var.project_name}-${var.environment}-oac"
  description                       = "OAC for ${var.project_name}-${var.environment} podcast bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                 = "always"
  signing_protocol                 = "sigv4"
}

# S3 Bucket policy for CloudFront OAC access
resource "aws_s3_bucket_policy" "podcast_bucket_policy" {
  bucket = aws_s3_bucket.podcast_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOriginAccessControl"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.podcast_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.podcast_distribution.arn
          }
        }
      }
    ]
  })

  depends_on = [
    aws_cloudfront_origin_access_control.podcast_oac,
    aws_cloudfront_distribution.podcast_distribution
  ]
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
    domain_name              = aws_s3_bucket.podcast_bucket.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.podcast_bucket.bucket}"
    origin_access_control_id = aws_cloudfront_origin_access_control.podcast_oac.id
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

  # Cache behavior for RSS feed - no caching to ensure fresh content
  ordered_cache_behavior {
    path_pattern           = "rss.xml"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.podcast_bucket.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true  # Forward query strings for cache-busting
      cookies {
        forward = "none"
      }
    }

    # Disable caching - always fetch from origin
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
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

# Download XML parser library
resource "null_resource" "download_xml_parser" {
  triggers = {
    script = filemd5("${path.module}/download-xml-parser.py")
  }

  provisioner "local-exec" {
    working_dir = path.module
    command     = "python download-xml-parser.py"
  }
}

# Upload XML parser library to S3
resource "aws_s3_object" "xml_parser_lib" {
  depends_on = [null_resource.download_xml_parser]
  bucket     = aws_s3_bucket.podcast_bucket.id
  key        = "lib/fast-xml-parser.min.js"
  source     = "${path.module}/lib/fast-xml-parser.min.js"
  etag       = filemd5("${path.module}/lib/fast-xml-parser.min.js")
  content_type = "application/javascript"

  tags = {
    Name        = "${var.project_name}-${var.environment}-xml-parser"
    Environment = var.environment
    Purpose     = "XML parser library for test player"
  }
}

# Upload test player HTML file to S3
resource "aws_s3_object" "test_player" {
  depends_on = [null_resource.download_xml_parser]
  bucket     = aws_s3_bucket.podcast_bucket.id
  key        = "test-player.html"
  source     = "${path.module}/test-player.html"
  etag       = filemd5("${path.module}/test-player.html")
  content_type = "text/html"

  tags = {
    Name        = "${var.project_name}-${var.environment}-test-player"
    Environment = var.environment
    Purpose     = "Podcast test player"
  }
}

# CloudFront cache invalidation for test player
# This invalidates the cache when test-player.html changes
# Using null_resource with AWS CLI since aws_cloudfront_invalidation may not be available
resource "null_resource" "cloudfront_invalidation" {
  depends_on = [aws_s3_object.test_player, aws_s3_object.xml_parser_lib]

  # Trigger invalidation when files change
  triggers = {
    test_player_etag = aws_s3_object.test_player.etag
    xml_parser_etag  = aws_s3_object.xml_parser_lib.etag
    distribution_id  = aws_cloudfront_distribution.podcast_distribution.id
  }

  provisioner "local-exec" {
    # Single-line command to avoid Windows cmd.exe line continuation issues
    # Paths must be passed as space-separated values without extra quotes around individual paths
    command = "aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.podcast_distribution.id} --paths /test-player.html /lib/fast-xml-parser.min.js --region ${var.aws_region}"
  }
}
