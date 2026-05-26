output "function_url" {
  description = "Lambda Function URL to call for dynamic DNS updates (GET with ip and api_key)"
  value       = aws_lambda_function_url.dynamic_dns.function_url
}

output "invoke_example" {
  description = "Example curl command (replace API_KEY and IP)"
  value       = "curl \"${aws_lambda_function_url.dynamic_dns.function_url}?ip=1.2.3.4&api_key=YOUR_API_KEY\""
}
