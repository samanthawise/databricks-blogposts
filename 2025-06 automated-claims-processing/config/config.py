# Databricks notebook source
# MAGIC %md
# MAGIC # Unified Configuration for AI-Powered Call Center Analytics
# MAGIC
# MAGIC This configuration file merges patterns from both source projects:
# MAGIC - Widget-based parameters for flexible deployment
# MAGIC - Helper functions for endpoint and resource management
# MAGIC - Unified catalog/schema/volume initialization
# MAGIC - Configuration for Whisper transcription endpoint
# MAGIC - Foundation model endpoints for AI analysis

# COMMAND ----------

# DBTITLE 1,Configuration Parameters
import time
from typing import Optional

# Widget-based configuration for flexibility across environments
dbutils.widgets.text("CATALOG", "call_center_analytics", label="CATALOG")
dbutils.widgets.text("SCHEMA", "main", label="SCHEMA")
dbutils.widgets.text("VOLUME", "call_center_data", label="VOLUME")
dbutils.widgets.dropdown("ENVIRONMENT", "dev", ["dev", "prod", "demo"], label="ENVIRONMENT")

# Get widget values
CATALOG = dbutils.widgets.get("CATALOG")
SCHEMA = dbutils.widgets.get("SCHEMA")
VOLUME = dbutils.widgets.get("VOLUME")
ENVIRONMENT = dbutils.widgets.get("ENVIRONMENT")

# COMMAND ----------

# DBTITLE 1,Table Names
# Bronze layer
BRONZE_TABLE = 'raw_audio_files'

# Silver layer
SILVER_TABLE = 'transcriptions_silver'

# Gold layer
GOLD_TABLE = 'call_analysis_gold'

# Lookup tables
CALL_REASONS_TABLE = 'call_reasons'
COMPLIANCE_GUIDELINES_TABLE = 'compliance_guidelines'

# Dashboard aggregation tables
DASHBOARD_METRICS_TABLE = 'dashboard_metrics'
DASHBOARD_TRENDS_TABLE = 'dashboard_trends'

# COMMAND ----------

# DBTITLE 1,Volume Directories
# Volume subdirectories
RAW_RECORDINGS_DIR = 'raw_recordings'
CHECKPOINTS_DIR = '_checkpoints'
SAMPLE_DATA_DIR = 'sample_data'

# Full paths
raw_audio_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{RAW_RECORDINGS_DIR}/"
checkpoint_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{CHECKPOINTS_DIR}/"
sample_data_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SAMPLE_DATA_DIR}/"

# COMMAND ----------

# DBTITLE 1,Endpoint Configuration
# Whisper transcription endpoint
WHISPER_ENDPOINT_NAME = "whisper-v3-large-pytorch"

# Foundation Model endpoints for AI Functions
LLM_ENDPOINT_REASONING = "databricks-claude-sonnet-4-5"  # For complex reasoning (compliance, email generation)
LLM_ENDPOINT_FAST = "databricks-gpt-5-nano"  # For fast operations (classification, sentiment)

# Agent integration (external Agent Bricks system)
AGENT_BRICKS_ENDPOINT = None  # To be configured when Agent Bricks is deployed

# COMMAND ----------

# DBTITLE 1,AI Analysis Prompts and Schemas

# Email generation prompt
EMAIL_GENERATION_PROMPT = """Generate a professional follow-up email based on this call transcript.
The email should:
- Address the customer's main concerns from the call
- Provide clear next steps
- Include any relevant policy information discussed
- Maintain a professional and empathetic tone
- Be concise (under 300 words)

Transcript: """

# Email JSON schema for structured output
EMAIL_JSON_SCHEMA = """{
  "type": "object",
  "properties": {
    "subject": {
      "type": "string",
      "description": "Email subject line"
    },
    "body": {
      "type": "string",
      "description": "Email body content"
    },
    "priority": {
      "type": "string",
      "enum": ["high", "normal", "low"],
      "description": "Email priority level"
    },
    "action_required": {
      "type": "boolean",
      "description": "Whether customer action is required"
    },
    "followup_date": {
      "type": "string",
      "description": "Suggested follow-up date (YYYY-MM-DD format)"
    }
  },
  "required": ["subject", "body", "priority"]
}"""

# Compliance evaluation prompt
COMPLIANCE_PROMPT = """Evaluate this call transcript for compliance with the following guidelines:
{guidelines}

Provide:
1. A compliance score from 0-100
2. List any violations or concerns
3. Recommendations for improvement

Transcript: """

# COMMAND ----------

# DBTITLE 1,Helper Functions - Catalog and Schema Management

def use_and_create_db(catalog: str, schema: str) -> None:
    """Create and use specified catalog and schema."""
    spark.sql(f"USE CATALOG `{catalog}`")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{schema}`")

def initialize_catalog_schema_volume(catalog: str, schema: str, volume: str) -> None:
    """Initialize Unity Catalog resources."""
    # Validate catalog name
    assert catalog not in ['hive_metastore', 'spark_catalog'], \
        "Cannot use hive_metastore or spark_catalog"

    # Create catalog if it doesn't exist
    current_catalog = spark.sql("SELECT current_catalog()").collect()[0]['current_catalog()']
    if current_catalog != catalog:
        catalogs = [r['catalog'] for r in spark.sql("SHOW CATALOGS").collect()]
        if catalog not in catalogs:
            spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
            print(f"✓ Created catalog: {catalog}")

    # Create schema
    use_and_create_db(catalog, schema)
    print(f"✓ Using catalog: {catalog}")
    print(f"✓ Using schema: {schema}")

    # Create volume
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume}`")
    print(f"✓ Created volume: {volume}")

    # Set current context
    spark.sql(f"USE CATALOG `{catalog}`")
    spark.sql(f"USE SCHEMA `{schema}`")

# COMMAND ----------

# DBTITLE 1,Helper Functions - Endpoint Management

def endpoint_exists(endpoint_name: str) -> bool:
    """Check if a Model Serving endpoint exists."""
    from databricks.sdk import WorkspaceClient

    try:
        w = WorkspaceClient()
        endpoints = w.serving_endpoints.list()
        return any(ep.name == endpoint_name for ep in endpoints)
    except Exception as e:
        if "REQUEST_LIMIT_EXCEEDED" in str(e):
            print(f"WARN: couldn't check endpoint status due to rate limit. Assuming it exists.")
            return True
        raise e

def get_endpoint_status(endpoint_name: str) -> dict:
    """Get the status of a Model Serving endpoint."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    try:
        endpoint = w.serving_endpoints.get(endpoint_name)
        return {
            "name": endpoint.name,
            "state": endpoint.state.ready if endpoint.state else "UNKNOWN",
            "config_update": endpoint.state.config_update if endpoint.state else "UNKNOWN"
        }
    except Exception as e:
        print(f"Error getting endpoint status: {e}")
        return {"name": endpoint_name, "state": "UNKNOWN", "error": str(e)}

def wait_for_endpoint_to_be_ready(endpoint_name: str, timeout_minutes: int = 30) -> None:
    """Wait for a Model Serving endpoint to be ready."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import EndpointStateReady, EndpointStateConfigUpdate

    w = WorkspaceClient()
    iterations = timeout_minutes * 6  # Check every 10 seconds

    print(f"Waiting for endpoint '{endpoint_name}' to be ready...")

    for i in range(iterations):
        try:
            endpoint = w.serving_endpoints.get(endpoint_name)
            state = endpoint.state

            if state.ready == EndpointStateReady.READY:
                print(f"✓ Endpoint '{endpoint_name}' is ready!")
                return

            if state.config_update == EndpointStateConfigUpdate.IN_PROGRESS:
                if i % 6 == 0:  # Print every minute
                    print(f"  Endpoint deploying... (state: {state})")
                time.sleep(10)
            else:
                print(f"  Unexpected state: {state}")
                time.sleep(10)
        except Exception as e:
            if i % 6 == 0:
                print(f"  Error checking endpoint: {e}")
            time.sleep(10)

    raise Exception(f"Timeout waiting for endpoint '{endpoint_name}' to be ready after {timeout_minutes} minutes")

def test_endpoint(endpoint_name: str, test_input: dict) -> dict:
    """Test a Model Serving endpoint with sample input."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    try:
        response = w.serving_endpoints.query(endpoint_name, inputs=[test_input])
        print(f"✓ Endpoint '{endpoint_name}' test successful")
        return response
    except Exception as e:
        print(f"✗ Endpoint test failed: {e}")
        raise e

# COMMAND ----------

# DBTITLE 1,Helper Functions - Utility

def get_checkpoint_path(layer: str) -> str:
    """Get checkpoint path for a specific pipeline layer."""
    return f"{checkpoint_path}{layer}/"

def table_exists(table_name: str) -> bool:
    """Check if a table exists in the current catalog/schema."""
    full_table_name = f"{CATALOG}.{SCHEMA}.{table_name}"
    return spark._jsparkSession.catalog().tableExists(full_table_name)

def print_config_summary() -> None:
    """Print a summary of the current configuration."""
    print("=" * 60)
    print("AI-POWERED CALL CENTER ANALYTICS - CONFIGURATION")
    print("=" * 60)
    print(f"Environment:       {ENVIRONMENT}")
    print(f"Catalog:           {CATALOG}")
    print(f"Schema:            {SCHEMA}")
    print(f"Volume:            {VOLUME}")
    print("-" * 60)
    print("Tables:")
    print(f"  Bronze:          {BRONZE_TABLE}")
    print(f"  Silver:          {SILVER_TABLE}")
    print(f"  Gold:            {GOLD_TABLE}")
    print(f"  Lookup:          {CALL_REASONS_TABLE}, {COMPLIANCE_GUIDELINES_TABLE}")
    print("-" * 60)
    print("Endpoints:")
    print(f"  Whisper:         {WHISPER_ENDPOINT_NAME}")
    print(f"  LLM (Reasoning): {LLM_ENDPOINT_REASONING}")
    print(f"  LLM (Fast):      {LLM_ENDPOINT_FAST}")
    print("-" * 60)
    print("Paths:")
    print(f"  Raw Audio:       {raw_audio_path}")
    print(f"  Checkpoints:     {checkpoint_path}")
    print(f"  Sample Data:     {sample_data_path}")
    print("=" * 60)

# COMMAND ----------

# DBTITLE 1,Initialize Resources (Run on Import)

# Initialize catalog, schema, and volume
initialize_catalog_schema_volume(CATALOG, SCHEMA, VOLUME)

# Print configuration summary
print_config_summary()

print("\n✓ Configuration loaded successfully!")
print(f"  Run notebooks with: CATALOG={CATALOG}, SCHEMA={SCHEMA}, VOLUME={VOLUME}")
