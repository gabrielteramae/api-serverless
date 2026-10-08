import json
import os
import string
import random
import time
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

CODE_LENGTH = 7
CODE_ALPHABET = string.ascii_letters + string.digits


def generate_short_code() -> str:
    return "".join(random.choices(CODE_ALPHABET, k=CODE_LENGTH))


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Corpo da requisição não é um JSON válido."})

    original_url = body.get("url", "").strip()
    if not original_url:
        return _response(400, {"error": "Campo 'url' é obrigatório."})

    if not (original_url.startswith("http://") or original_url.startswith("https://")):
        return _response(400, {"error": "A URL deve começar com http:// ou https://."})

    if len(original_url) > 2048:
        return _response(400, {"error": "A URL passou de 2048 caracteres."})

    # Gera um código curto único, tentando de novo em caso de colisão rara
    for _ in range(5):
        short_code = generate_short_code()
        try:
            table.put_item(
                Item={
                    "shortCode": short_code,
                    "originalUrl": original_url,
                    "createdAt": int(time.time()),
                    "clickCount": 0,
                },
                # Garante atomicidade: só grava se o código ainda não existir
                ConditionExpression="attribute_not_exists(shortCode)",
            )
            break
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            continue
    else:
        return _response(500, {"error": "Não foi possível gerar um código único. Tente novamente."})

    base_url = event.get("requestContext", {}).get("domainName", "")
    stage = event.get("requestContext", {}).get("stage", "")
    short_url = f"https://{base_url}/{stage}/{short_code}" if base_url else f"/{short_code}"

    return _response(201, {
        "shortCode": short_code,
        "shortUrl": short_url,
        "originalUrl": original_url,
    })


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
