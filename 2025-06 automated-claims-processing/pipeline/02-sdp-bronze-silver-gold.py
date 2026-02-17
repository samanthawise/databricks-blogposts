# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer Pipeline: AI-Powered Call Center Analytics
# MAGIC
# MAGIC This notebook focuses on the **Gold Layer** enrichment using existing transcription data:
# MAGIC - **Silver Layer**: Reads existing call transcriptions (skips audio processing for now)
# MAGIC - **Gold Layer**: Comprehensive AI enrichment (sentiment, summary, classification, NER, compliance, email generation)
# MAGIC
# MAGIC **Current Mode**: Using simulated/existing transcription data
# MAGIC
# MAGIC **AI Enrichments Applied**:
# MAGIC - Sentiment analysis with `ai_analyze_sentiment()`
# MAGIC - Call summarization with `ai_summarize()`
# MAGIC - Dynamic classification with `ai_classify()`
# MAGIC - Named entity recognition with `ai_extract()`
# MAGIC - PII masking with `ai_mask()`
# MAGIC - Compliance scoring with `ai_query()`
# MAGIC - Follow-up email generation with structured JSON output
# MAGIC
# MAGIC **Note**: Bronze layer (audio ingestion) and Silver layer (transcription) can be enabled later

# COMMAND ----------

# DBTITLE 1,Install Dependencies
# MAGIC %pip install -U --quiet mutagen
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Import Audio Processing Utilities
# MAGIC %run ./audio_processing_utils

# COMMAND ----------

# DBTITLE 1,Pipeline Configuration

from pyspark.sql import functions as F
from pyspark.sql.types import *

# Note: Checkpoint paths are only needed if using streaming mode
# Current implementation uses batch processing for better performance with small datasets
# Uncomment below if you want to use Auto Loader streaming:
# BRONZE_CHECKPOINT = get_checkpoint_path("bronze")
# SILVER_CHECKPOINT = get_checkpoint_path("silver")
# GOLD_CHECKPOINT = get_checkpoint_path("gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥉 Bronze Layer: Skip for Simulated Data
# MAGIC
# MAGIC **Note:** For this demo, we're skipping the Bronze layer (audio ingestion) and using existing transcription data.
# MAGIC
# MAGIC To enable Bronze layer with real audio files:
# MAGIC 1. Upload audio files to Unity Catalog volume
# MAGIC 2. Uncomment the Bronze layer code below
# MAGIC 3. Configure Whisper endpoint for transcription

# COMMAND ----------

# DBTITLE 1,Bronze Layer - Skipped (Using Existing Data)

print("ℹ️  Skipping Bronze layer - using existing transcription data")
print("   To process audio files, uncomment the Bronze layer code")

# Uncomment below to enable Bronze layer with audio file ingestion:
#
# print(f"Ingesting audio files from: {raw_audio_path}")
# bronze_df = (spark.read
#     .format("binaryFile")
#     .option("recursiveFileLookup", "true")
#     .load(raw_audio_path)
# )
# bronze_table = f"{CATALOG}.{SCHEMA}.{BRONZE_TABLE}"
# bronze_df.write.format("delta").mode("append").saveAsTable(bronze_table)
# print(f"✓ Bronze layer complete: {bronze_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥈 Silver Layer: Load Synthetic Call Data
# MAGIC
# MAGIC Loads pre-generated synthetic call data with transcriptions:
# MAGIC 1. Reads from `synthetic_call_data` table (created by sample_data_generator.py)
# MAGIC 2. Contains call metadata (call_id, agent_id, datetime, customer info)
# MAGIC 3. Includes simulated transcripts for testing AI enrichment
# MAGIC 4. Prepares data for Gold layer processing
# MAGIC
# MAGIC **Note**: In production, this would read from actual transcribed audio files

# COMMAND ----------

# DBTITLE 1,Silver Layer - Load Synthetic Call Data

print("Loading synthetic call data...")

# Read from the synthetic_call_data table (contains simulated transcripts)
silver_table = f"{CATALOG}.{SCHEMA}.synthetic_call_data"

try:
    # Load the table
    silver_raw = spark.table(silver_table)
    silver_count = silver_raw.count()
    print(f"✓ Loaded {silver_count} calls from: {silver_table}")

    # Prepare Silver DataFrame with standardized column names
    # Map 'transcript' column to 'transcription' for consistency with Gold layer
    silver_df = silver_raw.select(
        F.col("call_id"),
        F.col("agent_id"),
        F.col("call_datetime"),
        F.col("customer_name"),
        F.col("phone_number"),
        F.col("policy_number"),
        F.col("duration_seconds"),
        F.col("transcript").alias("transcription"),  # Rename for Gold layer
        F.col("filename"),
        F.col("category"),
        F.col("reason_for_call")
    )

    # Show sample
    print(f"\n📊 Silver Data Sample:")
    display(silver_df.select(
        "call_id", "agent_id", "call_datetime", "transcription"
    ).limit(3))

except Exception as e:
    print(f"✗ Could not load synthetic call data: {e}")
    print(f"\nPlease ensure the table exists: {silver_table}")
    print("Run the sample_data_generator.py notebook to create it")
    raise e

# Note: To enable audio transcription with Whisper endpoint in the future:
# 1. Uncomment the Bronze layer code to ingest audio files
# 2. Configure the Whisper endpoint properly
# 3. Add transcription step using ai_query() before Gold layer processing

# COMMAND ----------

# DBTITLE 1,Verify Silver Table

print(f"\n📊 Silver Table Ready for Gold Layer Processing")
print(f"  Table: {silver_table}")
print(f"  Proceeding to Gold Layer enrichment...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold Layer: AI-Powered Enrichment
# MAGIC
# MAGIC Applies comprehensive AI analysis to transcribed calls:
# MAGIC 1. **Sentiment Analysis**: Detect customer emotion
# MAGIC 2. **Summarization**: Generate concise call summaries
# MAGIC 3. **Classification**: Categorize call reason (dynamic from lookup table)
# MAGIC 4. **Named Entity Recognition (NER)**: Extract customer information
# MAGIC 5. **PII Masking**: Mask sensitive information
# MAGIC 6. **Compliance Scoring**: Evaluate agent compliance with guidelines
# MAGIC 7. **Follow-up Email Generation**: Create structured email drafts

# COMMAND ----------

# DBTITLE 1,Prepare AI Function Parameters

# Fetch call reasons from lookup table for dynamic classification
reasons_df = spark.table(f"{CATALOG}.{SCHEMA}.{CALL_REASONS_TABLE}")
reasons_list = [row['reason_for_call'] for row in reasons_df.select("reason_for_call").distinct().collect()]
reasons_sql_array = "ARRAY(" + ", ".join([f"'{r}'" for r in reasons_list]) + ")"

print(f"Call reasons for classification: {reasons_list[:5]}... ({len(reasons_list)} total)")

# Fetch compliance guidelines
compliance_df = spark.table(f"{CATALOG}.{SCHEMA}.{COMPLIANCE_GUIDELINES_TABLE}")
compliance_guidelines = compliance_df.selectExpr(
    "concat_ws(': ', guideline_id, title, description, concat('(Severity: ', severity, ')'))"
).collect()
guidelines_text = "\\n".join([row[0] for row in compliance_guidelines])

print(f"\nCompliance guidelines loaded: {len(compliance_guidelines)} guidelines")

# NER extraction targets
ner_targets_array = "ARRAY('person', 'policy_number', 'date', 'phone', 'email')"

# Email generation prompt (from config with escaping for SQL)
email_prompt_sql = EMAIL_GENERATION_PROMPT.replace("'", "\\'").replace("\n", "\\n")

# Email JSON schema (from config with escaping for SQL)
email_schema_sql = EMAIL_JSON_SCHEMA.replace("'", "\\'").replace("\n", "\\n")

# Compliance prompt
compliance_prompt_template = f"""Evaluate this call transcript for compliance with these guidelines:

{guidelines_text}

Provide a compliance analysis with:
1. Overall score (0-100, where 100 is perfect compliance)
2. List of specific violations (empty array if none)
3. Brief recommendations

Transcript: """

compliance_prompt_sql = compliance_prompt_template.replace("'", "\\'").replace("\n", "\\n")

# COMMAND ----------

# DBTITLE 1,Gold Layer - AI Enrichment

print("Applying AI enrichment with multiple AI functions...")

# Read from Silver table (batch mode for better performance)
gold_input_df = spark.table(silver_table)

# First, create the base transformations
gold_df = gold_input_df.selectExpr(
    "*",
    # Sentiment analysis
    "ai_analyze_sentiment(transcription) AS sentiment",

    # Summarization (100 words)
    "ai_summarize(transcription, 100) AS summary",

    # Classification - dynamic categories from lookup table
    f"ai_classify(transcription, {reasons_sql_array}) AS classification",

    # Named Entity Recognition
    f"ai_extract(transcription, {ner_targets_array}) AS entities",

    # PII Masking
    "ai_mask(transcription, ARRAY('person', 'phone', 'email', 'address')) AS masked_transcript"
)

# Write intermediate Gold table
gold_table_intermediate = f"{CATALOG}.{SCHEMA}.call_analysis_gold_intermediate"

gold_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable(gold_table_intermediate)

print(f"✓ Intermediate Gold layer complete: {gold_table_intermediate}")

# COMMAND ----------

# DBTITLE 1,Gold Layer - Advanced AI Enrichment (Batch)

# Now process the intermediate table with complex AI functions in batch mode
# This avoids streaming limitations with nested complex queries

print("Applying advanced AI enrichment (compliance scoring, email generation)...")

gold_intermediate = spark.table(gold_table_intermediate)

# Add compliance scoring and email generation
gold_intermediate.createOrReplaceTempView("gold_intermediate_temp")

final_gold_query = f"""
SELECT
    *,
    -- Compliance scoring with structured output
    ai_query(
        '{LLM_ENDPOINT_REASONING}',
        CONCAT('{compliance_prompt_sql}', transcription),
        returnType => 'STRUCT<score:INT, violations:ARRAY<STRING>, recommendations:STRING>'
    ) AS compliance_analysis,

    -- Follow-up email generation with JSON schema
    ai_query(
        '{LLM_ENDPOINT_REASONING}',
        CONCAT('{email_prompt_sql}', transcription),
        responseFormat => '{email_schema_sql}'
    ) AS follow_up_email
FROM gold_intermediate_temp
"""

final_gold_df = spark.sql(final_gold_query)

# Flatten NER entities for easier access
final_gold_df = final_gold_df \
    .withColumn("customer_name", F.col("entities.person")) \
    .withColumn("policy_number_extracted", F.col("entities.policy_number")) \
    .withColumn("dates_mentioned", F.col("entities.date")) \
    .withColumn("phone_numbers", F.col("entities.phone")) \
    .withColumn("email_addresses", F.col("entities.email"))

# Write final Gold table
gold_table = f"{CATALOG}.{SCHEMA}.{GOLD_TABLE}"

final_gold_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .option("overwriteSchema", "true") \
    .saveAsTable(gold_table)

print(f"✓ Final Gold layer complete: {gold_table}")

# Clean up intermediate table (optional)
# spark.sql(f"DROP TABLE IF EXISTS {gold_table_intermediate}")

# COMMAND ----------

# DBTITLE 1,Verify Gold Table

gold_count = spark.table(gold_table).count()

print(f"\n📊 Gold Table Statistics:")
print(f"  Table: {gold_table}")
print(f"  Total enriched calls: {gold_count}")
print(f"\n✓ Pipeline complete: Bronze → Silver → Gold")

if gold_count > 0:
    # Display summary columns
    display(spark.table(gold_table).select(
        "call_id",
        "agent_id",
        "call_datetime",
        "sentiment",
        "summary",
        "classification",
        "compliance_analysis.score",
        "follow_up_email.subject"
    ).limit(10))

# COMMAND ----------

# DBTITLE 1,Pipeline Execution Summary

print("\n" + "=" * 80)
print("GOLD LAYER PIPELINE EXECUTION SUMMARY")
print("=" * 80)

# Count records from synthetic data and gold table
silver_cnt = spark.table(silver_table).count()
gold_cnt = spark.table(gold_table).count()

print(f"\n📊 Record Counts:")
print(f"  Silver (Synthetic Calls): {silver_cnt}")
print(f"  Gold (AI Enriched):       {gold_cnt}")

print(f"\n✅ Tables Used/Created:")
print(f"  Input:  {silver_table}")
print(f"  Output: {gold_table}")

print(f"\n🔍 AI Enrichments Applied:")
print(f"  ✓ Sentiment Analysis")
print(f"  ✓ Call Summarization")
print(f"  ✓ Call Reason Classification ({len(reasons_list)} categories)")
print(f"  ✓ Named Entity Recognition (person, policy, date, phone, email)")
print(f"  ✓ PII Masking")
print(f"  ✓ Compliance Scoring ({len(compliance_guidelines)} guidelines)")
print(f"  ✓ Follow-up Email Generation")

print(f"\n🚀 Next Steps:")
print(f"  1. Query Gold table for analytics: SELECT * FROM {gold_table}")
print(f"  2. Create UC Functions: tools/03-create-uc-tools.py")
print(f"  3. Prepare dashboard: notebooks/05-prepare-dashboard-data.py")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Sample Gold Table Query

# COMMAND ----------

# DBTITLE 1,Query Gold Table - Compliance Issues

display(spark.sql(f"""
SELECT
    call_id,
    agent_id,
    call_datetime,
    classification,
    sentiment,
    compliance_analysis.score as compliance_score,
    compliance_analysis.violations as violations,
    summary
FROM {gold_table}
WHERE compliance_analysis.score < 80  -- Show calls with compliance issues
ORDER BY compliance_analysis.score ASC
LIMIT 10
"""))

# COMMAND ----------

# DBTITLE 1,Query Gold Table - Sentiment Analysis

display(spark.sql(f"""
SELECT
    sentiment,
    COUNT(*) as call_count,
    AVG(compliance_analysis.score) as avg_compliance_score,
    AVG(duration_seconds) as avg_duration
FROM {gold_table}
GROUP BY sentiment
ORDER BY call_count DESC
"""))

# COMMAND ----------

# DBTITLE 1,Query Gold Table - Call Reasons

display(spark.sql(f"""
SELECT
    classification,
    COUNT(*) as call_count,
    AVG(duration_seconds) as avg_duration,
    AVG(compliance_analysis.score) as avg_compliance
FROM {gold_table}
GROUP BY classification
ORDER BY call_count DESC
LIMIT 10
"""))
