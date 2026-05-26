# Dynamic DNS Lambda

Updates a single Route53 A record via a public GET URL. Intended for home/office IP updates (e.g. `home.example.com`).

## Setup

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set `zone_id`, `record_name`, and `api_key`.
2. Run `terraform init` then `terraform apply`.
3. Use the output `function_url` to call the endpoint.

## Usage

**GET** the Function URL with query parameters:

- `ip` – IPv4 address to set for the A record (required).
- `api_key` – Your secret API key (required).

Example:

```bash
curl "https://<function-url>?ip=203.0.113.42&api_key=YOUR_API_KEY"
```

Success: `200` with JSON `{"updated": "home.example.com", "ip": "203.0.113.42"}`.  
Errors: `400` (bad/missing `ip`), `403` (wrong/missing `api_key`), `500` (config or Route53 error).

## Security

- IAM is limited to the single hosted zone (one zone ID). The Lambda code only updates the one record named in `record_name`.
- Auth is via `api_key` in the query string (no custom headers). Use HTTPS only and a long random key; treat the URL as secret.

## State

Terraform state is stored in the same S3 bucket as the podcast stack, under key `dynamic-dns/terraform.tfstate`.
