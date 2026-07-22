import os
os.environ["TABLE_NAME"] = "ShortUrls-test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

from moto import mock_aws
import boto3
import json
import sys
sys.path.insert(0, "../src/create_url")

@mock_aws
def run_tests():
    # Cria a tabela fake antes de importar o handler (que já cria a referência à tabela)
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="ShortUrls-test",
        KeySchema=[{"AttributeName": "shortCode", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "shortCode", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    import app  # importa DEPOIS da tabela existir

    print("== Teste 1: criar URL válida ==")
    event = {
        "body": json.dumps({"url": "https://github.com/gabrielteramae"}),
        "requestContext": {"domainName": "abc123.execute-api.us-east-1.amazonaws.com", "stage": "prod"},
    }
    result = app.handler(event, None)
    print(result)
    assert result["statusCode"] == 201, "Deveria retornar 201"
    body = json.loads(result["body"])
    assert "shortCode" in body and len(body["shortCode"]) == 7
    assert body["originalUrl"] == "https://github.com/gabrielteramae"
    print("✅ passou\n")

    print("== Teste 2: URL vazia deve falhar ==")
    event2 = {"body": json.dumps({"url": ""}), "requestContext": {}}
    result2 = app.handler(event2, None)
    print(result2)
    assert result2["statusCode"] == 400
    print("✅ passou\n")

    print("== Teste 3: URL sem http(s):// deve falhar ==")
    event3 = {"body": json.dumps({"url": "github.com/gabrielteramae"}), "requestContext": {}}
    result3 = app.handler(event3, None)
    print(result3)
    assert result3["statusCode"] == 400
    print("✅ passou\n")

    print("== Teste 4: JSON malformado deve falhar ==")
    event4 = {"body": "{isso nao e json", "requestContext": {}}
    result4 = app.handler(event4, None)
    print(result4)
    assert result4["statusCode"] == 400
    print("✅ passou\n")

    print("== Teste 5: verificar que o item foi gravado com os campos certos ==")
    table = dynamodb.Table("ShortUrls-test")
    item = table.get_item(Key={"shortCode": body["shortCode"]})["Item"]
    print(item)
    assert item["clickCount"] == 0
    assert item["originalUrl"] == "https://github.com/gabrielteramae"
    assert "createdAt" in item
    print("✅ passou\n")

    print("🎉 TODOS OS TESTES PASSARAM")

run_tests()
