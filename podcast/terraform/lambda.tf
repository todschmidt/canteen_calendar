# IAM role for Lambda function
resource "aws_iam_role" "rss_generator_role" {
  name = "${var.project_name}-${var.environment}-rss-generator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-rss-generator-role"
    Environment = var.environment
  }
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "rss_generator_policy" {
  name = "${var.project_name}-${var.environment}-rss-generator-policy"
  role = aws_iam_role.rss_generator_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.podcast_bucket.arn,
          "${aws_s3_bucket.podcast_bucket.arn}/*"
        ]
      }
    ]
  })
}

# Lambda function for RSS generation
resource "aws_lambda_function" "rss_generator" {
  filename         = "rss_generator.zip"
  function_name    = "${var.project_name}-${var.environment}-rss-generator"
  role            = aws_iam_role.rss_generator_role.arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.rss_generator_zip.output_base64sha256
  runtime         = "python3.13"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.podcast_bucket.bucket
      PODCAST_TITLE = var.podcast_title
      PODCAST_DESCRIPTION = var.podcast_description
      PODCAST_AUTHOR = var.podcast_author
      PODCAST_EMAIL = var.podcast_email
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.podcast_distribution.domain_name
      DOMAIN_NAME = var.domain_name != "" ? "${var.subdomain}.${var.domain_name}" : ""
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rss-generator"
    Environment = var.environment
  }
}

# Create the Lambda function zip file
data "archive_file" "rss_generator_zip" {
  type        = "zip"
  output_path = "rss_generator.zip"
  source {
    content = templatefile("${path.module}/lambda_function.py", {
      bucket_name = aws_s3_bucket.podcast_bucket.bucket
      podcast_title = var.podcast_title
      podcast_description = var.podcast_description
      podcast_author = var.podcast_author
      podcast_email = var.podcast_email
      cloudfront_domain = aws_cloudfront_distribution.podcast_distribution.domain_name
      domain_name = var.domain_name != "" ? "${var.subdomain}.${var.domain_name}" : ""
    })
    filename = "index.py"
  }
}

# S3 event trigger for Lambda
resource "aws_s3_bucket_notification" "podcast_bucket_notification" {
  bucket = aws_s3_bucket.podcast_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.rss_generator.arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = ""
    filter_suffix       = ".mp3"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# Lambda permission for S3 to invoke the function
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rss_generator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.podcast_bucket.arn
}
