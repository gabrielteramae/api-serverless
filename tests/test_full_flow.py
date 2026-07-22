import os
os.environ["TABLE_NAME"] = "ShortUrls-test-clean"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

from moto import mock_aws
import boto3
import json
import sys


@mock_aws
def run():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="ShortUrls-test-clean",
        KeySchema=[{"AttributeName": "shortCode", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "shortCode", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    sys.path.insert(0, "../src/create_url")
    import app as create_app
    create_handler = create_app.handler
    del sys.modules["app"]

    sys.path.insert(0, "../src/redirect")
    import app as redirect_app
    redirect_handler = redirect_app.handler
    del sys.modules["app"]

    sys.path.insert(0, "../src/get_stats")
    import app as stats_app
    stats_handler = stats_app.handler
    del sys.modules["app"]

    print("== 1. Criar URL curta ==")
    create_event = {
        "body": json.dumps({"url": "https://gabrielteramae.github.io/meu-portfolio/"}),
        "requestContext": {"domainName": "xyz.execute-api.us-east-1.amazonaws.com", "stage": "prod"},
    }
    create_result = create_handler(create_event, None)
    print(create_result)
    assert create_result["statusCode"] == 201
    body = json.loads(create_result["body"])
    short_code = body["shortCode"]
    print(f"Código gerado: {short_code}\n")

    print("== 2. Redirecionar 3 vezes ==")
    for i in range(3):
        redirect_result = redirect_handler({"pathParameters": {"shortCode": short_code}}, None)
        print(f"  Tentativa {i+1}: status={redirect_result['statusCode']} location={redirect_result['headers'].get('Location')}")
        assert redirect_result["statusCode"] == 302
        assert redirect_result["headers"]["Location"] == "https://gabrielteramae.github.io/meu-portfolio/"

    print("\n== 3. Redirecionar código inexistente (deve dar 404) ==")
    bad_result = redirect_handler({"pathParameters": {"shortCode": "naoexiste"}}, None)
    print(f"  status={bad_result['statusCode']}")
    assert bad_result["statusCode"] == 404

    print("\n== 4. Conferir estatísticas (esperado: 3 cliques) ==")
    stats_result = stats_handler({"pathParameters": {"shortCode": short_code}}, None)
    stats_body = json.loads(stats_result["body"])
    print(f"  {stats_body}")
    assert stats_result["statusCode"] == 200
    assert stats_body["clickCount"] == 3, f"Esperava 3 cliques, veio {stats_body['clickCount']}"

    print("\n== 5. Estatística de código inexistente (deve dar 404) ==")
    bad_stats = stats_handler({"pathParameters": {"shortCode": "xxxxxxx"}}, None)
    print(f"  status={bad_stats['statusCode']}")
    assert bad_stats["statusCode"] == 404

    print("\n🎉 FLUXO COMPLETO PASSOU: criar → redirecionar 3x → estatísticas corretas → 404s corretos")


run()
