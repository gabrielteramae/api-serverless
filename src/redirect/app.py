import os
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, context):
    short_code = event.get("pathParameters", {}).get("shortCode")
    if not short_code:
        return _redirect_error(400, "Código curto não informado.")

    # Incrementa o contador de cliques atomicamente e já retorna o item atualizado
    # (evita a condição de corrida de fazer get + put separados)
    try:
        result = table.update_item(
            Key={"shortCode": short_code},
            UpdateExpression="ADD clickCount :inc",
            ExpressionAttributeValues={":inc": 1},
            ConditionExpression="attribute_exists(shortCode)",
            ReturnValues="ALL_NEW",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _redirect_error(404, "Código curto não encontrado.")

    original_url = result["Attributes"]["originalUrl"]

    # 302 Found: redireciona sem cachear no navegador (permite continuar contando cliques)
    return {
        "statusCode": 302,
        "headers": {"Location": original_url},
        "body": "",
    }


def _redirect_error(status_code: int, message: str):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": f'{{"error": "{message}"}}',
    }
