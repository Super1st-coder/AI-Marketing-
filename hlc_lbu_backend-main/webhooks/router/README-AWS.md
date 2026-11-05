# webhook-router (AWS Version)

Esta es la guía de implementación de AWS para el Webhook Router. Convive con la implementación de GCP (`README.md`).

## Arquitectura

- **GCP:** API Gateway → Cloud Functions Gen 2 → Pub/Sub
- **AWS:** Application Load Balancer (o HTTP API Gateway) → AWS Lambda → AWS SNS

## Despliegue en AWS

### 1. Variables de entorno (Locales o GitHub Actions)
Asegúrate de tener configurado tu perfil de AWS CLI (`aws configure`) o las variables de entorno de AWS.

### 2. Infraestructura
El API Gateway, los Roles IAM, los SNS Topics y una Lambda inicial se crean automáticamente usando Terraform en `hlc_inf_base`. Todo se basa en las definiciones existentes de `registry.py`.

### 3. Empaquetar y Desplegar el Código
La infraestructura de Terraform crea la función Lambda, pero el código real debe subirse después.

```bash
# Entrar a la carpeta del router
cd hlc_lbu_backend/webhooks/router

# Instalar las dependencias localmente en la carpeta para empaquetarlas
pip install -r requirements-aws.txt -t .

# Crear el archivo zip (excluyendo tests, caché y archivos innecesarios)
zip -r function.zip . -i "*.py" "registry.py" "verifiers.py" "lambda_function.py" "boto3/*" "botocore/*" "jmespath/*" "s3transfer/*" "urllib3/*"

# Subir a AWS Lambda (asegúrate que el nombre coincide con tu entorno, ej. dev)
aws lambda update-function-code \
  --function-name hiluca-lbu-dev-webhook-router \
  --zip-file fileb://function.zip \
  --region us-east-2

# Opcional: Limpiar el zip
rm function.zip
```

### 4. Obtener la URL (API Gateway HTTP API)
La URL base se obtiene de los outputs de Terraform:

```bash
cd ../../../hlc_inf_base/amazon/infra
terraform output webhook_api_url

# Ejemplo: https://<api-id>.execute-api.us-east-2.amazonaws.com
# URL final: https://<api-id>.execute-api.us-east-2.amazonaws.com/webhook/appsflyer/v1.0.0/prd
```

### 5. Secretos
Para que la firma funcione, debes crear el valor del secreto manualmente (ya que Terraform solo crea la carcasa vacía).
Ejemplo:

```bash
aws secretsmanager put-secret-value \
  --secret-id hiluca-lbu-dev-wh-secret-appsflyer \
  --secret-string "EL_SECRETO_REAL_AQUI"
```

---

## Flujo de vida de un webhook en AWS

```
1.  Proveedor → POST /webhook/appsflyer/v1.0.0/prd
2.  AWS API Gateway → AWS Lambda (lambda_function.py)
3.  Router parsea path → servicio=appsflyer, version=v1.0.0, entorno=prd
4.  Lookup SERVICE_REGISTRY → obtiene config
5.  Carga secret "hiluca-lbu-dev-wh-secret-appsflyer" desde AWS Secrets Manager
6.  Valida firma HMAC-SHA256 con header "x-signature"
      → ❌ Firma inválida → 401
      → ✅ Firma válida → continúa
7.  Genera idempotency_key = "appsflyer:v1.0.0:prd:<appsflyer_id>"
8.  Publica en SNS topic "hiluca-lbu-dev-wh-appsflyer-prd" con atributos
9.  Retorna 200 {"status": "ok", "message_id": "..."}
10. [Async] Lambda procesadora o SQS Queue consume el evento desde SNS
```
