# Databricks notebook source
# MAGIC %md
# MAGIC # Setup: Initialize Call Center Analytics Environment
# MAGIC
# MAGIC This notebook initializes the complete environment for AI-Powered Call Center Analytics:
# MAGIC - Creates Unity Catalog resources (catalog, schema, volumes)
# MAGIC - Creates lookup tables (call_reasons, compliance_guidelines)
# MAGIC - Sets up volume directory structure
# MAGIC - Verifies Foundation Model endpoints are accessible
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Unity Catalog enabled in workspace
# MAGIC - Access to Databricks Foundation Model endpoints

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Reset Data (Optional)
dbutils.widgets.dropdown("reset_all_data", "false", ["false", "true"], "Reset All Data")

reset_all_data = dbutils.widgets.get("reset_all_data") == "true"

if reset_all_data:
    print("⚠️  WARNING: Resetting all data...")
    try:
        # Drop tables
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{BRONZE_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{SILVER_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{GOLD_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{CALL_REASONS_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{COMPLIANCE_GUIDELINES_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{DASHBOARD_METRICS_TABLE}")
        spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{DASHBOARD_TRENDS_TABLE}")

        # Clean volume directories
        dbutils.fs.rm(raw_audio_path, True)
        dbutils.fs.rm(checkpoint_path, True)
        dbutils.fs.rm(sample_data_path, True)

        print("✓ All data reset successfully")
    except Exception as e:
        print(f"Note: Some resources may not exist yet: {e}")
else:
    print("Skipping data reset (set widget to 'true' to reset)")

# COMMAND ----------

# DBTITLE 1,Create Volume Directory Structure
print("Creating volume directory structure...")

# Create subdirectories
dbutils.fs.mkdirs(raw_audio_path)
dbutils.fs.mkdirs(checkpoint_path)
dbutils.fs.mkdirs(sample_data_path)

print(f"✓ Created directory: {raw_audio_path}")
print(f"✓ Created directory: {checkpoint_path}")
print(f"✓ Created directory: {sample_data_path}")

# COMMAND ----------

# DBTITLE 1,Create Call Reasons Lookup Table
print("Creating call reasons lookup table...")

# Define call reasons and next steps
call_reasons_data = [
    # Standard call reasons
    ("Claim status inquiry", "Provide claim status update", "general"),
    ("Coverage details request", "Explain coverage details", "general"),
    ("Billing and premium question", "Assist with billing", "general"),
    ("Finding in-network provider", "Find in-network provider", "general"),
    ("Policy renewal", "Initiate policy renewal", "general"),
    ("Updating personal details", "Update customer details", "general"),
    ("Technical support", "Provide technical support", "general"),
    ("Filing a new claim", "File new claim request", "general"),
    ("Canceling a policy", "Process policy cancellation", "general"),

    # Financial hardship reasons (will be classified as "Financial hardship")
    ("Requesting premium payment deferral due to financial hardship", "Review eligibility for payment deferral", "financial_hardship"),
    ("Inquiry about hardship assistance programs", "Explain available financial hardship assistance options", "financial_hardship"),
    ("Request to lower coverage temporarily due to income loss", "Adjust policy coverage as requested", "financial_hardship"),

    # Fraud detection
    ("Fraudulent claim attempt", "Escalate suspected fraud", "fraud"),

    # Additional common reasons
    ("Pre-authorization request", "Process pre-authorization", "general"),
    ("Appeal claim denial", "Initiate appeal process", "general"),
    ("Change beneficiary", "Update beneficiary information", "general"),
    ("Request policy documents", "Send policy documents", "general"),
    ("Complaint about service", "Log complaint and escalate", "general")
]

from pyspark.sql import Row
from pyspark.sql.functions import when, col

# Create DataFrame
df_reasons = spark.createDataFrame(
    [Row(reason_for_call=r[0], next_steps=r[1], category=r[2]) for r in call_reasons_data]
)

# Map financial hardship reasons to "Financial hardship" category for classification
df_reasons = df_reasons.withColumn(
    "reason_for_call",
    when(col("category") == "financial_hardship", "Financial hardship")
    .otherwise(col("reason_for_call"))
)

# Save as table
df_reasons.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.{CALL_REASONS_TABLE}"
)

print(f"✓ Created table: {CATALOG}.{SCHEMA}.{CALL_REASONS_TABLE}")
print(f"  Total reasons: {df_reasons.count()}")

# Display sample data
display(df_reasons.limit(5))

# COMMAND ----------

# DBTITLE 1,Create Compliance Guidelines Lookup Table
print("Creating compliance guidelines lookup table...")

# Define compliance guidelines for call center operations
compliance_guidelines_data = [
    {
        "guideline_id": "CG001",
        "category": "data_privacy",
        "title": "Customer Information Protection",
        "description": "Agent must not share customer personal information without proper verification",
        "severity": "critical"
    },
    {
        "guideline_id": "CG002",
        "category": "professional_conduct",
        "title": "Professional Communication",
        "description": "Agent must maintain professional and courteous tone throughout the call",
        "severity": "high"
    },
    {
        "guideline_id": "CG003",
        "category": "data_privacy",
        "title": "Payment Card Information",
        "description": "Agent must not request or record full payment card numbers over the phone",
        "severity": "critical"
    },
    {
        "guideline_id": "CG004",
        "category": "disclosure",
        "title": "Policy Terms Disclosure",
        "description": "Agent must clearly explain policy terms, limitations, and exclusions when discussed",
        "severity": "high"
    },
    {
        "guideline_id": "CG005",
        "category": "documentation",
        "title": "Accurate Record Keeping",
        "description": "Agent must accurately document all customer interactions and commitments",
        "severity": "medium"
    },
    {
        "guideline_id": "CG006",
        "category": "fraud_prevention",
        "title": "Fraud Detection",
        "description": "Agent must escalate suspicious claims or identity verification failures",
        "severity": "critical"
    },
    {
        "guideline_id": "CG007",
        "category": "regulatory",
        "title": "HIPAA Compliance",
        "description": "Agent must follow HIPAA guidelines when discussing health information",
        "severity": "critical"
    },
    {
        "guideline_id": "CG008",
        "category": "customer_rights",
        "title": "Right to Appeal",
        "description": "Agent must inform customers of their right to appeal claim denials",
        "severity": "high"
    },
    {
        "guideline_id": "CG009",
        "category": "professional_conduct",
        "title": "No Guarantee of Outcomes",
        "description": "Agent must not guarantee specific claim outcomes or approval",
        "severity": "high"
    },
    {
        "guideline_id": "CG010",
        "category": "call_quality",
        "title": "Call Recording Notice",
        "description": "Agent must inform customers that calls are recorded at the beginning",
        "severity": "medium"
    }
]

# Create DataFrame
df_compliance = spark.createDataFrame([Row(**item) for item in compliance_guidelines_data])

# Save as table
df_compliance.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.{COMPLIANCE_GUIDELINES_TABLE}"
)

print(f"✓ Created table: {CATALOG}.{SCHEMA}.{COMPLIANCE_GUIDELINES_TABLE}")
print(f"  Total guidelines: {df_compliance.count()}")

# Display sample data
display(df_compliance.limit(5))

# Create summary text for use in AI compliance analysis
compliance_summary = df_compliance.selectExpr(
    "concat_ws(': ', guideline_id, title, description) as guideline_text"
).collect()

compliance_guidelines_text = "\n".join([row.guideline_text for row in compliance_summary])

print("\n📋 Compliance Guidelines Summary (for AI analysis):")
print("-" * 60)
print(compliance_guidelines_text)
print("-" * 60)

# COMMAND ----------

# DBTITLE 1,Verify Foundation Model Endpoints
print("Verifying Foundation Model endpoints are accessible...")

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Check each required endpoint
endpoints_to_check = [
    ("LLM (Reasoning)", LLM_ENDPOINT_REASONING),
    ("LLM (Fast)", LLM_ENDPOINT_FAST)
]

all_endpoints_available = True

for endpoint_label, endpoint_name in endpoints_to_check:
    try:
        if endpoint_exists(endpoint_name):
            status = get_endpoint_status(endpoint_name)
            if status["state"] == "READY" or "READY" in str(status["state"]):
                print(f"✓ {endpoint_label}: {endpoint_name} is ready")
            else:
                print(f"⚠️  {endpoint_label}: {endpoint_name} exists but state is {status['state']}")
                all_endpoints_available = False
        else:
            print(f"✗ {endpoint_label}: {endpoint_name} not found")
            all_endpoints_available = False
    except Exception as e:
        print(f"✗ Error checking {endpoint_label} ({endpoint_name}): {e}")
        all_endpoints_available = False

# Note about Whisper endpoint
print(f"\nNote: Whisper endpoint '{WHISPER_ENDPOINT_NAME}' will be deployed in notebook 01-deploy-whisper-endpoint.py")

if all_endpoints_available:
    print("\n✓ All Foundation Model endpoints are available!")
else:
    print("\n⚠️  Some endpoints are not available. Please check your workspace configuration.")
    print("   Foundation Model endpoints should be available by default in most Databricks workspaces.")

# COMMAND ----------

# DBTITLE 1,Setup Summary
print("\n" + "=" * 80)
print("SETUP COMPLETE - AI-POWERED CALL CENTER ANALYTICS")
print("=" * 80)
print(f"\n✓ Catalog: {CATALOG}")
print(f"✓ Schema: {SCHEMA}")
print(f"✓ Volume: {VOLUME}")
print(f"\n✓ Lookup Tables Created:")
print(f"  - {CALL_REASONS_TABLE} ({df_reasons.count()} reasons)")
print(f"  - {COMPLIANCE_GUIDELINES_TABLE} ({df_compliance.count()} guidelines)")
print(f"\n✓ Volume Directories:")
print(f"  - {raw_audio_path}")
print(f"  - {checkpoint_path}")
print(f"  - {sample_data_path}")
print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Run setup/01-deploy-whisper-endpoint.py to deploy Whisper transcription endpoint")
print("2. Run setup/sample_data_generator.py to generate demo data (optional)")
print("3. Create Lakeflow SDP pipeline with pipeline/02-sdp-bronze-silver-gold.py")
print("=" * 80)
