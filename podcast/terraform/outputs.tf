output "s3_bucket_name" {
  description = "Name of the S3 bucket for podcast files"
  value       = aws_s3_bucket.podcast_bucket.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.podcast_bucket.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.podcast_bucket.bucket_domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.podcast_distribution.id
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.podcast_distribution.domain_name
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.podcast_distribution.arn
}

output "rss_feed_url" {
  description = "URL of the RSS feed"
  value       = var.domain_name != "" ? "https://${var.subdomain}.${var.domain_name}/rss.xml" : "https://${aws_cloudfront_distribution.podcast_distribution.domain_name}/rss.xml"
}

output "domain_name" {
  description = "Custom domain name for the podcast"
  value       = var.domain_name != "" ? "${var.subdomain}.${var.domain_name}" : null
}

output "lambda_function_name" {
  description = "Name of the Lambda function for RSS generation"
  value       = aws_lambda_function.rss_generator.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.rss_generator.arn
}

output "acm_certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.podcast_cert[0].arn : null
}

output "test_player_url" {
  description = "URL of the test player HTML page"
  value       = var.domain_name != "" ? "https://${var.subdomain}.${var.domain_name}/test-player.html" : "https://${aws_cloudfront_distribution.podcast_distribution.domain_name}/test-player.html"
}
