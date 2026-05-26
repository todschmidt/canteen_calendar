"""
Dynamic DNS Lambda: update a single Route53 A record via GET request.
GET params: ip (IPv4), api_key (required).
"""
import os
import json
import ipaddress
import logging

import boto3

ROUTE53 = boto3.client("route53")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # Lambda Function URL: client IP is in requestContext.http.sourceIp
    request_context = event.get("requestContext") or {}
    http_ctx = request_context.get("http") or {}
    client_ip = http_ctx.get("sourceIp") or request_context.get("identity", {}).get("sourceIp") or "unknown"

    query = event.get("queryStringParameters") or {}
    ip = (query.get("ip") or "").strip()
    api_key = (query.get("api_key") or "").strip()

    logger.info(
        "Request received",
        extra={
            "client_ip": client_ip,
            "ip_param_present": ip,
            "api_key_present": bool(api_key),
        },
    )

    expected_key = os.environ.get("API_KEY", "")
    zone_id = os.environ.get("ZONE_ID", "")
    record_name = os.environ.get("RECORD_NAME", "home")

    if not expected_key or not zone_id:
        logger.error("Server misconfiguration: missing API_KEY or ZONE_ID env")
        return response(500, "Server misconfiguration (missing env)")

    if not api_key or api_key != expected_key:
        logger.warning("Forbidden: invalid or missing api_key", extra={"client_ip": client_ip})
        return response(403, "Forbidden")

    if not ip:
        logger.warning("Bad request: missing ip", extra={"client_ip": client_ip})
        return response(400, "Missing parameter: ip")

    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        logger.warning("Bad request: invalid IPv4", extra={"client_ip": client_ip, "ip_param": ip})
        return response(400, "Invalid IPv4: " + ip)

    logger.info(
        "Updating A record",
        extra={"client_ip": client_ip, "ip_being_set": ip, "record_name": record_name},
    )

    try:
        zone = ROUTE53.get_hosted_zone(Id=zone_id)
        zone_name = zone["HostedZone"]["Name"].rstrip(".")
        fqdn = f"{record_name}.{zone_name}" if record_name else zone_name
        if not fqdn.endswith("."):
            fqdn += "."
    except Exception as e:
        logger.exception("Failed to get hosted zone", extra={"client_ip": client_ip, "zone_id": zone_id})
        return response(500, "Failed to get zone: " + str(e))

    change_batch = {
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": fqdn,
                    "Type": "A",
                    "TTL": 300,
                    "ResourceRecords": [{"Value": ip}],
                },
            }
        ]
    }

    try:
        ROUTE53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch=change_batch,
        )
    except Exception as e:
        logger.exception(
            "Route53 update failed",
            extra={"client_ip": client_ip, "ip_being_set": ip, "fqdn": fqdn.rstrip(".")},
        )
        return response(500, "Route53 update failed: " + str(e))

    logger.info(
        "A record updated successfully",
        extra={
            "client_ip": client_ip,
            "ip_set": ip,
            "fqdn": fqdn.rstrip("."),
        },
    )
    return response(200, json.dumps({"updated": fqdn.rstrip("."), "ip": ip}))


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": body,
    }
