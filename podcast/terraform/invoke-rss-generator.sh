#!/bin/bash
# Manually invoke the RSS generator Lambda with optional debug payload.
#
# Usage:
#   ./invoke-rss-generator.sh                  # normal run
#   ./invoke-rss-generator.sh --debug          # verbose CloudWatch logs
#   ./invoke-rss-generator.sh --skip-metadata  # skip audio downloads (fast test)
#   ./invoke-rss-generator.sh --dry-run        # build RSS but don't upload
#   ./invoke-rss-generator.sh --limit 3        # process only 3 files
#   ./invoke-rss-generator.sh --tail             # invoke then tail CloudWatch logs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FUNCTION_NAME="${FUNCTION_NAME:-$(terraform output -raw lambda_function_name 2>/dev/null || echo 'cedar-mountain-podcast-dev-rss-generator')}"
PAYLOAD='{}'
TAIL_LOGS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            PAYLOAD=$(echo "$PAYLOAD" | jq '. + {"debug": true}')
            ;;
        --skip-metadata)
            PAYLOAD=$(echo "$PAYLOAD" | jq '. + {"skip_metadata": true}')
            ;;
        --dry-run)
            PAYLOAD=$(echo "$PAYLOAD" | jq '. + {"dry_run": true}')
            ;;
        --limit)
            shift
            PAYLOAD=$(echo "$PAYLOAD" | jq --argjson limit "$1" '. + {"limit": $limit}')
            ;;
        --tail)
            TAIL_LOGS=true
            ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
    shift
done

OUTFILE="$(mktemp)"
echo "Invoking $FUNCTION_NAME"
echo "Payload: $PAYLOAD"
echo ""

aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "$PAYLOAD" \
    --cli-binary-format raw-in-base64-out \
    "$OUTFILE"

echo "Response:"
cat "$OUTFILE"
echo ""
rm -f "$OUTFILE"

if [[ "$TAIL_LOGS" == true ]]; then
    echo ""
    echo "Tailing recent CloudWatch logs (Ctrl+C to stop)..."
    LOG_GROUP="/aws/lambda/$FUNCTION_NAME"
    aws logs tail "$LOG_GROUP" --since 5m --follow
fi
