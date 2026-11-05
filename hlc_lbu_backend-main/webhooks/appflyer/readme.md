gcloud functions deploy appflyer-events-processor \
  --gen2 \
  --runtime python312 \
  --region us-central1 \
  --trigger-topic appflyer-events \
  --entry-point pubsub_handler \
  --service-account=401654669410-compute@developer.gserviceaccount.com \
  --source processor/ \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,BIGQUERY_DATASET=appflyer_events,BIGQUERY_TABLE=events_structured,ENCRYPTION_KEY="asds"


gcloud functions deploy appflyer-webhook \
  --gen2 \
  --runtime python312 \
  --region us-central1 \
  --trigger-http \
  --no-allow-unauthenticated \
  --source rest/ \
  --entry-point webhook_entry_point \
  --set-env-vars PUBSUB_TOPIC=appflyer-events,GOOGLE_CLOUD_PROJECT=careful-acumen-422922-k4

# Deploy API Gateway configuration with GET and POST support
gcloud api-gateway api-configs create appflyer-webhook-config-v2 \
  --api=appflyer-webhook-api \
  --openapi-spec=api-config.yaml \
  --project=careful-acumen-422922-k4

# Update the gateway to use the new config
gcloud api-gateway gateways update appflyer-webhook-gw \
  --api=appflyer-webhook-api \
  --api-config=appflyer-webhook-config-v2 \
  --location=us-central1 \
  --project=careful-acumen-422922-k4

# Grant API Gateway service account permission to invoke Cloud Functions
gcloud projects add-iam-policy-binding careful-acumen-422922-k4 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/cloudfunctions.invoker"

# Grant API Gateway service account permission to access the function
gcloud functions add-iam-policy-binding appflyer-webhook \
  --region=us-central1 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/cloudfunctions.invoker"


  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:<SERVICE_ACCOUNT_WEBHOOK>" \
  --role="roles/pubsub.publisher"


  python simulator/simulate_appsflyer_postbacks.py \
  --url "https://appflyer-webhook-gw-54imtiea.uc.gateway.dev/" \
  --secret "asds" \
  --app-id "com.test.app" \
  --types "install" \
  --count 1


  python simulator/simulate_appsflyer_postbacks.py \
  --url "https://integrate.hiluca.com/" \
  --secret "asds" \
  --app-id "com.test.app" \
  --types "install" \
  --count 1

# Test GET request (simulating AppsFlyer GET webhook)
curl -X GET "https://integrate.hiluca.com/?site_id=com.oakever.tiletrip&ad=320x50&ad_is=420897&adset=&adset_id=&android_device_id=78dcb307-c837-46ec-8cf4-6b89581be100&app_id=com.walmartmexico.wallet&app_name=Cashi&app_version=3.14.1&appsflyer_id=1759120377943-1151206261788078472&campaign=Cashi%7CRocket%7CGeneral%7CACQ%7CGeneral%7CPilto-ACQ&event_name=PAYMENT_SUCCESS&event_revenue=&event_revenue_usd=&event_revenue_currency=USD&event_time=2025-10-03%2021%3A21%3A12.015&even_value=%7B%22TRANSACTION_AMOUNT%22%3A%2250.00%22%2C%22TIMESTAMP%22%3A%221759526471698%22%2C%22BANKNAME%22%3A%22HSBC%20PR%22%2C%22BRANDTYPE%22%3A%22VISA%22%2C%22TRANSACTION_TYPE%22%3A%22BILL_PAY%22%2C%22PAYMENT_METHOD%22%3A%22wallet%2CdebitCard%22%7D&install_time=2025-10-03%2020%3A19%3A17.239&platform=android&click_id=jYtmpe_TUwlJ5s_zDQ1ziu&cost_currency=&cost_model=&cost_value="

# Test POST request
curl -X POST "https://integrate.hiluca.com/" \
  -H "Content-Type: application/json" \
  -d '{"app_id": "com.test.app", "event": "install", "platform": "android"}'

# Check API Gateway status
gcloud api-gateway gateways describe appflyer-webhook-gw \
  --location=us-central1 \
  --project=careful-acumen-422922-k4

# Check API Gateway logs
gcloud logging read "resource.type=api_gateway" \
  --project=careful-acumen-422922-k4 \
  --limit=10 \
  --format="table(timestamp,severity,textPayload)"

gcloud functions logs read appflyer-webhook --gen2 --region=us-central1 --limit=50

gcloud functions logs read appflyer-events-processor --gen2 --region=us-central1 --limit=50



gcloud pubsub topics list --format='value(name)' | grep appflyer-events || \
gcloud pubsub topics create appflyer-events


gcloud functions describe appflyer-events-processor \
  --gen2 --region=us-central1 \
  --format='yaml(name,environment,eventTrigger,serviceConfig.service,serviceConfig.uri,serviceConfig.entryPoint)'


gcloud run services add-iam-policy-binding appflyer-events-processor \
  --region=us-central1 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"


  PROJECT_NUMBER=401654669410
TRIGGER_SA="401654669410-compute@developer.gserviceaccount.com"

# Autoriza al service agent de Eventarc a emitir tokens para ese SA
gcloud iam service-accounts add-iam-policy-binding "$TRIGGER_SA" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

# Autoriza al service agent de Pub/Sub (conector de Eventarc) a emitir tokens para ese SA
gcloud iam service-accounts add-iam-policy-binding "$TRIGGER_SA" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

gcloud pubsub topics add-iam-policy-binding appflyer-events \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

gcloud run services add-iam-policy-binding appflyer-events-processor \
  --region=us-central1 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud eventarc triggers describe appflyer-events-processor-878131 \
  --location=us-central1 \
  --format='yaml(name,transport.pubsub.topic,destination,serviceAccount,conditions)'

gcloud eventarc triggers describe appflyer-events-processor-878131 \
  --location=us-central1 \
  --format='yaml(name,transport.pubsub.topic,destination,serviceAccount,conditions)'



PROJECT_ID="careful-acumen-422922-k4"
TRIGGER_SA="401654669410-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${TRIGGER_SA}" \
  --role="roles/eventarc.eventReceiver"





  bq --location=US mk \
  --dataset careful-acumen-422922-k4:appflyer_events

  bq query --use_legacy_sql=false "
CREATE TABLE \`careful-acumen-422922-k4.appflyer_events.events_encrypted\` (
  ingest_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  event_time  TIMESTAMP,
  event       STRING,
  app_id      STRING,
  platform    STRING,
  payload_json STRING
)
PARTITION BY DATE(ingest_time)
CLUSTER BY app_id, event;
"



gcloud projects add-iam-policy-binding careful-acumen-422922-k4 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding careful-acumen-422922-k4 \
  --member="serviceAccount:401654669410-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"



bq --project_id=careful-acumen-422922-k4 ls -d | grep appflyer_events || \
bq mk --dataset --location=US careful-acumen-422922-k4:appflyer_events

bq show --format=prettyjson careful-acumen-422922-k4:appflyer_events > ds.json


bq update --source=ds.json careful-acumen-422922-k4:appflyer_events


# Create new structured table
bq query --use_legacy_sql=false '
CREATE TABLE IF NOT EXISTS `careful-acumen-422922-k4.appflyer_events.events_structured` (
  -- Core event fields
  ingest_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  event_time TIMESTAMP,
  event STRING,
  app_id STRING,
  platform STRING,
  install_time TIMESTAMP,
  
  -- Event-specific fields
  event_name STRING,
  event_revenue STRING,
  event_revenue_usd STRING,
  event_revenue_currency STRING,
  even_value STRING,
  
  -- Event value details (extracted from even_value JSON)
  transaction_amount STRING,
  transaction_timestamp STRING,
  bank_name STRING,
  brand_type STRING,
  transaction_type STRING,
  payment_method STRING,
  
  -- App information
  app_name STRING,
  app_version STRING,
  sdk_version STRING,
  
  -- Device identifiers
  android_device_id STRING,
  appsflyer_id STRING,
  af_user_id STRING,
  advertising_id STRING,
  android_id STRING,
  customer_user_id STRING,
  idfa STRING,
  idfv STRING,
  gaid STRING,
  
  -- Location and language
  country_code STRING,
  language STRING,
  ip STRING,
  
  -- Attribution fields
  site_id STRING,
  ad STRING,
  ad_is STRING,
  adset STRING,
  adset_id STRING,
  campaign STRING,
  click_id STRING,
  
  -- Cost information
  cost_currency STRING,
  cost_model STRING,
  cost_value STRING,
  
  -- Attribution object (as JSON for complex attribution data)
  af_attribution JSON,
  media_source STRING,
  is_retargeting BOOLEAN,
  
  -- Raw payload for debugging/backup
  payload_json STRING
)
PARTITION BY DATE(ingest_time)
CLUSTER BY app_id, event, event_name;'

# Migrate existing data from old table to new structured table
bq query --use_legacy_sql=false < migrate_data.sql



gcloud domains verify hiluca.com


gcloud certificate-manager dns-authorizations create integrate-hiluca-dns \
  --domain=integrate.hiluca.com --location=global

gcloud certificate-manager certificates create integrate-hiluca-cert \
  --domains=integrate.hiluca.com \
  --dns-authorizations=integrate-hiluca-dns \
  --location=global



  gcloud compute network-endpoint-groups create apigw-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --serverless-deployment-platform=apigateway.googleapis.com \
  --serverless-deployment-resource=appflyer-webhook-gw-54imtiea


  REGION=us-central1
PROJECT=careful-acumen-422922-k4
GATEWAY_NAME=appflyer-webhook-gw-54imtiea
NEG_NAME=neg-apigw-integrate
BS_NAME=bs-apigw-integrate

gcloud compute network-endpoint-groups create $NEG_NAME \
  --region=$REGION \
  --network-endpoint-type=serverless \
  --serverless-deployment-platform=apigateway \
  --serverless-gateway=$GATEWAY_NAME


  gcloud api-gateway gateways update $GATEWAY_NAME \
  --location=$REGION \
  --project=$PROJECT \
  --custom-domain=integrate.hiluca.com \
  --certificate=projects/$PROJECT/locations/global/certificates/integrate-hiluca-cert


REGION="us-central1" 
GATEWAY="appflyer-webhook-gw" 
CUSTOM_DOMAIN="integrate.hiluca.com"
CERT_NAME="integrate-hiluca-cert"


PROJECT="careful-acumen-422922-k4"
REGION="us-central1"         
GATEWAY="appflyer-webhook-gw" 
NEG="gw-neg"
BACKEND="gw-backend"
URLMAP="gw-urlmap"
PROXY="gw-https-proxy"
FR="gw-https-fr"
IP_NAME="gw-ip"
DOMAIN="integrate.hiluca.com"
CERT_NAME="integrate-hiluca-cert"


gcloud beta compute network-endpoint-groups create "$NEG" \
  --project="$PROJECT" \
  --region="$REGION" \
  --network-endpoint-type=serverless \
  --serverless-deployment-platform=apigateway.googleapis.com \
  --serverless-deployment-resource="$GATEWAY"


  gcloud compute backend-services create "$BACKEND" --global --project="$PROJECT"


gcloud compute backend-services add-backend "$BACKEND" \
  --global --project="$PROJECT" \
  --network-endpoint-group="$NEG" \
  --network-endpoint-group-region="$REGION"


  gcloud compute url-maps create "$URLMAP" \
  --default-service="$BACKEND" \
  --project="$PROJECT"

  gcloud certificate-manager maps create hiluca-map --project="$PROJECT"


gcloud certificate-manager maps entries create hiluca-entry \
  --project="$PROJECT" \
  --map="hiluca-map" \
  --hostname="$DOMAIN" \
  --certificates="$CERT_NAME"


gcloud compute target-https-proxies create "$PROXY" \
  --project="$PROJECT" \
  --url-map="$URLMAP" \
  --global \
  --certificate-map="projects/$PROJECT/locations/global/certificateMaps/hiluca-map"


gcloud certificate-manager maps entries create hiluca-entry \
  --project="$PROJECT" \
  --map="hiluca-map" \
  --hostname="$DOMAIN" \
  --certificates="$CERT_NAME"

  gcloud compute target-https-proxies create "$PROXY" \
  --project="$PROJECT" \
  --url-map="$URLMAP" \
  --global \
  --certificate-map="projects/$PROJECT/locations/global/certificateMaps/hiluca-map"


  gcloud compute addresses create "$IP_NAME" --global --project="$PROJECT"



34.117.114.125