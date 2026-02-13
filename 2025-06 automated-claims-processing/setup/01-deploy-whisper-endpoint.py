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
    print("This may take 15-30 minutes...")
    print("\nNote: Secure egress gateway initialization can be slow.")
    print("If deployment times out, the endpoint may still be creating in the background.")

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

    # Create endpoint (without waiting initially)
    try:
        print(f"\nInitiating endpoint creation...")
        endpoint_response = w.serving_endpoints.create(
            name=ENDPOINT_NAME,
            config=config
        )
        print(f"✓ Endpoint creation initiated: {endpoint_response.name}")
        print(f"  Current state: {endpoint_response.state}")
        print(f"\n⏳ Endpoint is being created in the background...")
        print(f"   This process can take 15-30 minutes.")
        print(f"   You can continue to the next cell to monitor progress.")

    except Exception as e:
        error_msg = str(e)

        # Check if endpoint already exists (common race condition)
        if "already exists" in error_msg.lower():
            print(f"\n⚠️  Endpoint '{ENDPOINT_NAME}' already exists (possibly from previous attempt)")
            print(f"   Checking current status...")
            endpoint_exists_flag = True
        else:
            print(f"\n✗ Error creating endpoint: {e}")
            print(f"\nTroubleshooting steps:")
            print(f"1. Check if endpoint is already being created in Databricks UI → Serving")
            print(f"2. If so, wait for it to complete and run the next cell to check status")
            print(f"3. If error persists, contact Databricks support")
            raise e
else:
    print(f"Skipping deployment - using existing endpoint '{ENDPOINT_NAME}'")

# COMMAND ----------

# DBTITLE 1,Wait for Endpoint to be Ready (or Check Status)
print(f"Checking status of endpoint '{ENDPOINT_NAME}'...")
print("=" * 60)

# First check if endpoint exists
if not endpoint_exists(ENDPOINT_NAME):
    print(f"⚠️  Endpoint '{ENDPOINT_NAME}' not found.")
    print(f"   Please ensure the previous cell ran successfully.")
    print(f"   Or check Databricks UI → Serving for endpoint status.")
else:
    # Get current status
    current_status = get_endpoint_status(ENDPOINT_NAME)
    print(f"Endpoint: {ENDPOINT_NAME}")
    print(f"Status: {current_status}")
    print("=" * 60)

    # Check if ready
    try:
        from databricks.sdk.service.serving import EndpointStateReady
        endpoint_info = w.serving_endpoints.get(ENDPOINT_NAME)

        if endpoint_info.state and endpoint_info.state.ready == EndpointStateReady.READY:
            print(f"\n✅ Endpoint '{ENDPOINT_NAME}' is READY for inference!")
        else:
            print(f"\n⏳ Endpoint is still deploying...")
            print(f"   Current state: {endpoint_info.state}")
            print(f"\n   Options:")
            print(f"   1. Wait and re-run this cell in 5-10 minutes")
            print(f"   2. Check progress in Databricks UI → Serving → {ENDPOINT_NAME}")
            print(f"   3. Use the helper function below to wait:")
            print(f"\n   # Wait for endpoint (can take 15-30 minutes)")
            print(f"   wait_for_endpoint_to_be_ready('{ENDPOINT_NAME}', timeout_minutes=45)")

    except Exception as e:
        print(f"\n⚠️  Error checking endpoint: {e}")
        print(f"\nIf you see 'Secure egress gateway start up timed out':")
        print(f"  - The endpoint may still be creating in the background")
        print(f"  - Check Databricks UI → Serving → {ENDPOINT_NAME}")
        print(f"  - Wait 10-15 minutes and re-run this cell")
        print(f"  - If issue persists after 30 minutes, contact Databricks support")

# COMMAND ----------

# DBTITLE 1,(Optional) Wait Actively for Endpoint
# Run this cell only if you want to actively wait for endpoint to be ready
# This can take 15-30 minutes for first-time deployment

WAIT_FOR_READY = False  # Set to True to wait actively

if WAIT_FOR_READY:
    print("Actively waiting for endpoint to be ready...")
    print("This may take 15-30 minutes. You can safely interrupt and check status later.\n")

    try:
        import time
        from databricks.sdk.service.serving import EndpointStateReady

        max_wait_minutes = 45
        check_interval_seconds = 30
        elapsed_minutes = 0

        while elapsed_minutes < max_wait_minutes:
            try:
                endpoint = w.serving_endpoints.get(ENDPOINT_NAME)

                if endpoint.state and endpoint.state.ready == EndpointStateReady.READY:
                    print(f"\n✅ Endpoint is READY! (took ~{elapsed_minutes} minutes)")
                    break

                print(f"[{elapsed_minutes} min] Status: {endpoint.state} - Still deploying...")
                time.sleep(check_interval_seconds)
                elapsed_minutes += check_interval_seconds / 60

            except Exception as e:
                print(f"[{elapsed_minutes} min] Error checking status: {e}")
                print("Endpoint may still be initializing. Waiting...")
                time.sleep(check_interval_seconds)
                elapsed_minutes += check_interval_seconds / 60

        if elapsed_minutes >= max_wait_minutes:
            print(f"\n⚠️  Timeout after {max_wait_minutes} minutes.")
            print("Endpoint may still be deploying. Check Databricks UI → Serving")

    except KeyboardInterrupt:
        print("\n⚠️  Wait interrupted. Endpoint continues deploying in background.")
        print("Re-run previous cell to check current status.")
else:
    print("Skipping active wait. Run previous cell to check endpoint status.")

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
