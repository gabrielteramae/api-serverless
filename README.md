# Encurtador serverless — três Lambdas e uma tabela DynamoDB

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?logo=awslambda&logoColor=white)
![Amazon DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?logo=amazondynamodb&logoColor=white)
![AWS SAM](https://img.shields.io/badge/AWS_SAM-232F3E?logo=amazonaws&logoColor=white)

Encurtador separado em três funções (criar, redirecionar, estatística) atrás de um API Gateway. A tabela é DynamoDB on-demand, chave `shortCode`. O contador de cliques sobe com `ADD` atômico no próprio redirect.

## Por que três funções

| Escolha | Efeito |
| --- | --- |
| Uma Lambda por rota, no `template.yaml` | Timeout e memória iguais (5 s, 128 MB), mas o código de cada rota fica isolado. |
| Uma função que lê o path | Menos artefato. Um bug no redirect derruba a criação. |
| `put_item` com `attribute_not_exists(shortCode)` | Código de 7 caracteres; até 5 tentativas se colidir. |
| `update_item` com `ADD clickCount` | Não faz get e put separados, que perderiam clique concorrente. |
| HTTP 302, não 301 | O navegador não cacheia o destino, então o próximo acesso volta a contar. |

Não há TTL, autenticação nem alias. CORS libera `*` para GET, POST e OPTIONS. O clique incrementa quando a função responde, mesmo que o cliente ignore o `Location`.

## Stack

- Python 3.12 (runtime no `template.yaml`)
- AWS SAM (`AWS::Serverless-2016-10-31`)
- API Gateway, estágio `prod`
- DynamoDB `PAY_PER_REQUEST`
- boto3 nas funções (não há `requirements.txt`; a runtime da Lambda já traz boto3)
- Testes locais com `moto` (`mock_aws`), também sem versão pinada

## Estrutura

```
template.yaml
src/
├── create_url/app.py   # POST /urls
├── redirect/app.py     # GET /{shortCode}
└── get_stats/app.py    # GET /urls/{shortCode}/stats
tests/
├── test_create_url.py  # script, não pytest
└── test_full_flow.py
```

## Como rodar

Não há Dockerfile no repositório. O `sam local` puxa a imagem de runtime da AWS e exige Docker e AWS SAM CLI, que não estão declarados aqui.

```bash
git clone https://github.com/gabrielteramae/api-serverless.git
cd api-serverless
sam build
sam local start-api
```

Deploy (conta AWS, credenciais e bucket SAM à parte):

```bash
sam deploy --guided
```

A URL de saída do stack é `https://<api>.execute-api.<região>.amazonaws.com/prod/`.

## Endpoints

| Método | Rota | Resposta |
| --- | --- | --- |
| POST | `/urls` | 201 com `shortCode`, `shortUrl`, `originalUrl`. Corpo `{"url":"https://..."}` |
| GET | `/{shortCode}` | 302 com `Location` da URL original; 404 se o código não existe |
| GET | `/urls/{shortCode}/stats` | `shortCode`, `originalUrl`, `createdAt` (epoch), `clickCount` |

POST recusa JSON inválido, `url` vazia, sem `http://` ou `https://`, acima de 2048 caracteres, com usuário, senha ou espaço.

## Testes realizados

Não é suíte pytest e não há CI. Os dois arquivos são scripts com `moto.mock_aws` e uma tabela DynamoDB falsa.

- `test_create_url.py`: URL válida gera código de 7 caracteres e grava `clickCount` 0; URL vazia, sem esquema e JSON quebrado voltam 400.
- `test_full_flow.py`: cria, redireciona 3 vezes (302), confere `clickCount == 3`, e 404 no redirect e nas stats de código inexistente.

Os `sys.path` são relativos ao diretório atual (`../src/...`). Rode de dentro de `tests/`, com `boto3` e `moto` instalados (versões não pinadas):

```bash
pip install boto3 moto
cd tests
python test_create_url.py
python test_full_flow.py
```

---

© 2026 Gabriel Teramae Chan
