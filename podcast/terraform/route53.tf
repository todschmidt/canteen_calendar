# Route53 hosted zone data source (assuming the zone already exists)
data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = "${var.domain_name}."
}

# Route53 record for ACM certificate validation
resource "aws_route53_record" "cert_validation" {
  for_each = var.domain_name != "" ? {
    for dvo in aws_acm_certificate.podcast_cert[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

# Route53 record for CloudFront distribution
resource "aws_route53_record" "cloudfront" {
  count = var.domain_name != "" ? 1 : 0
  
  name    = "${var.subdomain}.${var.domain_name}"
  type    = "A"
  zone_id = data.aws_route53_zone.main[0].zone_id

  alias {
    name                   = aws_cloudfront_distribution.podcast_distribution.domain_name
    zone_id                = aws_cloudfront_distribution.podcast_distribution.hosted_zone_id
    evaluate_target_health = false
  }
}
