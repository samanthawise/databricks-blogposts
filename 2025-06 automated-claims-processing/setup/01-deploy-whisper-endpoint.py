# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy PyTorch Whisper v3 Large Endpoint
# MAGIC
# MAGIC This notebook deploys the Whisper Large v3 model to Databricks Model Serving for audio transcription.
# MAGIC
# MAGIC **Key Features:**
# MAGIC - Uses pre-trained `system.ai.whisper_large_v3` model from Unity Catalog
# MAGIC - Deploys with GPU compute for efficient transcription
# MAGIC - Configures for scale-to-zero to optimize costs
# MAGIC - Tests endpoint with sample audio (if available)
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Unity Catalog enabled
# MAGIC - Model Serving permissions
# MAGIC - GPU quota for endpoint deployment

# COMMAND ----------

# DBTITLE 1,Install Dependencies
# MAGIC %pip install -U --quiet databricks-sdk mlflow
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Endpoint Configuration
from datetime import timedelta
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput

# Unity Catalog path to Whisper model
MODEL_UC_PATH = "system.ai.whisper_large_v3"
MODEL_VERSION = "3"  # Latest version

# Endpoint name from config
ENDPOINT_NAME = WHISPER_ENDPOINT_NAME

# Workload configuration
# Use GPU_MEDIUM for AWS, GPU_LARGE for Azure
# Adjust based on your cloud provider and expected workload
WORKLOAD_TYPE = "GPU_MEDIUM"  # Options: GPU_SMALL, GPU_MEDIUM, GPU_LARGE
WORKLOAD_SIZE = "Small"  # Options: Small, Medium, Large

print("=" * 60)
print("WHISPER ENDPOINT CONFIGURATION")
print("=" * 60)
print(f"Model:          {MODEL_UC_PATH}")
print(f"Model Version:  {MODEL_VERSION}")
print(f"Endpoint Name:  {ENDPOINT_NAME}")
print(f"Workload Type:  {WORKLOAD_TYPE}")
print(f"Workload Size:  {WORKLOAD_SIZE}")
print("=" * 60)

# COMMAND ----------

# DBTITLE 1,Check if Endpoint Already Exists
w = WorkspaceClient()

if endpoint_exists(ENDPOINT_NAME):
    print(f"⚠️  Endpoint '{ENDPOINT_NAME}' already exists.")
    print(f"   Checking status...")

    status = get_endpoint_status(ENDPOINT_NAME)
    print(f"\n   Current state: {status}")

    # Provide options
    dbutils.widgets.dropdown("action", "use_existing", ["use_existing", "recreate"], "Action")
    action = dbutils.widgets.get("action")

    if action == "recreate":
        print(f"\n⚠️  Deleting existing endpoint '{ENDPOINT_NAME}'...")
        w.serving_endpoints.delete(ENDPOINT_NAME)
        print(f"✓ Endpoint deleted. Proceeding with new deployment...")
        endpoint_exists_flag = False
    else:
        print(f"\n✓ Using existing endpoint. Skipping deployment.")
        endpoint_exists_flag = True
else:
    print(f"✓ Endpoint '{ENDPOINT_NAME}' does not exist. Proceeding with deployment...")
    endpoint_exists_flag = False

# COMMAND ----------

# DBTITLE 1,Deploy Whisper Endpoint
if not endpoint_exists_flag:
    print(f"Deploying Whisper endpoint: {ENDPOINT_NAME}")
    print("This may take 10-15 minutes...")

    # Configure endpoint
    config = EndpointCoreConfigInput.from_dict({
        "served_models": [
            {
                "name": ENDPOINT_NAME,
                "model_name": MODEL_UC_PATH,
                "model_version": MODEL_VERSION,
                "workload_type": WORKLOAD_TYPE,
                "workload_size": WORKLOAD_SIZE,
                "scale_to_zero_enabled": True,
            }
        ]
    })

    # Create and wait for endpoint
    try:
        model_details = w.serving_endpoints.create_and_wait(
            name=ENDPOINT_NAME,
            config=config,
            timeout=timedelta(minutes=30)
        )
        print(f"\n✓ Endpoint '{ENDPOINT_NAME}' deployed successfully!")
        print(f"   Details: {model_details}")
    except Exception as e:
        print(f"\n✗ Error deploying endpoint: {e}")
        raise e
else:
    print(f"Skipping deployment - using existing endpoint '{ENDPOINT_NAME}'")

# COMMAND ----------

# DBTITLE 1,Wait for Endpoint to be Ready
print(f"Ensuring endpoint '{ENDPOINT_NAME}' is ready...")

try:
    wait_for_endpoint_to_be_ready(ENDPOINT_NAME, timeout_minutes=30)
    print(f"\n✓ Endpoint '{ENDPOINT_NAME}' is ready for inference!")
except Exception as e:
    print(f"\n✗ Error waiting for endpoint: {e}")
    raise e

# COMMAND ----------

# DBTITLE 1,Test Endpoint (Optional)
print("Testing Whisper endpoint...")

# Check if sample audio files exist
sample_audio_files = []
try:
    sample_audio_files = dbutils.fs.ls(raw_audio_path)
except Exception as e:
    print(f"No audio files found in {raw_audio_path}")
    print("Skipping endpoint test. You can test manually once audio files are uploaded.")

if len(sample_audio_files) > 0:
    print(f"Found {len(sample_audio_files)} audio file(s) in {raw_audio_path}")
    print("Testing endpoint with first audio file...\n")

    # Get first audio file
    test_audio_path = sample_audio_files[0].path

    # Read audio file as binary
    from pyspark.sql.functions import col

    df_test = spark.read.format("binaryFile").load(test_audio_path).limit(1)

    # Test transcription using ai_query
    df_transcription = df_test.selectExpr(
        "path",
        f"ai_query('{ENDPOINT_NAME}', content, returnType => 'STRING') as transcription"
    )

    # Display result
    result = df_transcription.collect()[0]
    print("=" * 60)
    print("TRANSCRIPTION TEST RESULT")
    print("=" * 60)
    print(f"Audio File: {result['path']}")
    print(f"\nTranscription:\n{result['transcription'][:500]}...")  # Show first 500 chars
    print("=" * 60)
    print("✓ Endpoint test successful!")
else:
    print("\n⚠️  No audio files available for testing.")
    print("   Upload audio files to test the endpoint:")
    print(f"   {raw_audio_path}")

# COMMAND ----------

# DBTITLE 1,Endpoint Deployment Summary
from datetime import datetime

print("\n" + "=" * 80)
print("WHISPER ENDPOINT DEPLOYMENT COMPLETE")
print("=" * 80)
print(f"Endpoint Name:     {ENDPOINT_NAME}")
print(f"Model:             {MODEL_UC_PATH} (version {MODEL_VERSION})")
print(f"Status:            Ready ✓")
print(f"Deployment Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n" + "=" * 80)
print("USAGE IN AI FUNCTIONS")
print("=" * 80)
print("Use this endpoint in SQL/PySpark with ai_query():")
print(f"""
SELECT
    ai_query(
        '{ENDPOINT_NAME}',
        audio_content,
        returnType => 'STRING'
    ) as transcription
FROM audio_table
""")
print("=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. Upload audio files to: " + raw_audio_path)
print("2. Run setup/sample_data_generator.py to generate demo data (optional)")
print("3. Create Lakeflow SDP pipeline: pipeline/02-sdp-bronze-silver-gold.py")
print("=" * 80)
