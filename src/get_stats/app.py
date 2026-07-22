import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, context):
    short_code = event.get("pathParameters", {}).get("shortCode")
    if not short_code:
        return _response(400, {"error": "Código curto não informado."})

    result = table.get_item(Key={"shortCode": short_code})
    item = result.get("Item")

    if item is None:
        return _response(404, {"error": "Código curto não encontrado."})

    return _response(200, {
        "shortCode": item["shortCode"],
        "originalUrl": item["originalUrl"],
        "createdAt": int(item["createdAt"]),
        "clickCount": int(item["clickCount"]),
    })


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
