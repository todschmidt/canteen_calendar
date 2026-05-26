# Zone name needed to build normalized record name for IAM condition
data "aws_route53_zone" "dynamic_dns" {
  zone_id = var.zone_id
}

# Normalized FQDN for IAM: lowercase, no trailing dot (required by route53 condition key)
locals {
  zone_name_no_dot = trimspace(trimsuffix(data.aws_route53_zone.dynamic_dns.name, "."))
  normalized_fqdn  = lower("${var.record_name}.${local.zone_name_no_dot}")
}

# IAM role for Lambda - strictly scoped to the single hosted zone
resource "aws_iam_role" "dynamic_dns" {
  name = "dynamic-dns-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Standalone policy: Route53 access only to the specified zone and record (IAM condition)
resource "aws_iam_policy" "dynamic_dns_route53" {
  name        = "dynamic-dns-route53"
  description = "Route53 access for dynamic-dns Lambda (single zone and record)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "route53:GetHostedZone"
        Resource = "arn:aws:route53:::hostedzone/${var.zone_id}"
      },
      {
        Effect   = "Allow"
        Action   = "route53:ChangeResourceRecordSets"
        Resource = "arn:aws:route53:::hostedzone/${var.zone_id}"
        Condition = {
          "ForAllValues:StringEquals" = {
            "route53:ChangeResourceRecordSetsNormalizedRecordNames" = [local.normalized_fqdn]
            "route53:ChangeResourceRecordSetsRecordTypes"           = ["A"]
            "route53:ChangeResourceRecordSetsActions"               = ["UPSERT"]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dynamic_dns_route53" {
  role       = aws_iam_role.dynamic_dns.name
  policy_arn = aws_iam_policy.dynamic_dns_route53.arn
}

# CloudWatch Logs for Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.dynamic_dns.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Package Lambda source
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/lambda.zip"
}

# Lambda function
resource "aws_lambda_function" "dynamic_dns" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "dynamic-dns"
  role             = aws_iam_role.dynamic_dns.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      API_KEY     = var.api_key
      ZONE_ID     = var.zone_id
      RECORD_NAME = var.record_name
    }
  }
}

# Lambda Function URL (public GET; auth via api_key query param)
resource "aws_lambda_function_url" "dynamic_dns" {
  function_name      = aws_lambda_function.dynamic_dns.function_name
  authorization_type = "NONE"
}

# Allow public invocation of the Function URL (required for NONE auth; app auth via api_key param)
# Both InvokeFunctionUrl and InvokeFunction are required for Function URL invocation (Oct 2025+)
resource "aws_lambda_permission" "function_url" {
  statement_id          = "AllowPublicFunctionUrlInvoke"
  action                = "lambda:InvokeFunctionUrl"
  function_name         = aws_lambda_function.dynamic_dns.function_name
  function_url_auth_type = "NONE"
  principal             = "*"
}

resource "aws_lambda_permission" "invoke_function" {
  statement_id  = "AllowPublicInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dynamic_dns.function_name
  principal     = "*"
}
