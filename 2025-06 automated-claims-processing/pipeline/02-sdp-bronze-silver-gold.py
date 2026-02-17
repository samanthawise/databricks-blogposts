# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver → Gold Pipeline: Call Center Analytics
# MAGIC
# MAGIC This notebook implements a complete Bronze → Silver → Gold pipeline using:
# MAGIC - **Bronze Layer**: Batch ingestion of audio files from Unity Catalog volumes
# MAGIC - **Silver Layer**: Audio transcription using Whisper endpoint via `ai_query()`
# MAGIC - **Gold Layer**: Comprehensive AI enrichment (sentiment, summary, classification, NER, compliance, email generation)
# MAGIC
# MAGIC **Architecture**: Medallion Architecture with batch processing (optimized for small/medium datasets)
# MAGIC
# MAGIC **Key Features**:
# MAGIC - Efficient batch processing for fast execution with small datasets
# MAGIC - Production-ready Whisper transcription via Model Serving
# MAGIC - Multiple AI functions for comprehensive call analysis
# MAGIC - Structured outputs with JSON schemas
# MAGIC - Dynamic classification from lookup tables
# MAGIC
# MAGIC **Note**: For large-scale production with continuous ingestion, consider using Auto Loader streaming

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
# MAGIC ## 🥉 Bronze Layer: Ingest Raw Audio Files
# MAGIC
# MAGIC Batch ingestion of audio files from Unity Catalog volume.
# MAGIC - Reads audio files as binary format
# MAGIC - Fast processing for small to medium datasets
# MAGIC - For large-scale continuous ingestion, consider Auto Loader streaming

# COMMAND ----------

# DBTITLE 1,Bronze Layer - Raw Audio File Ingestion

print(f"Ingesting audio files from: {raw_audio_path}")

# For small datasets, use batch reading for better performance
# For large-scale production with many files, consider using Auto Loader streaming
bronze_df = (spark.read
    .format("binaryFile")
    .option("recursiveFileLookup", "true")
    .load(raw_audio_path)
)

# Write to Bronze table
bronze_table = f"{CATALOG}.{SCHEMA}.{BRONZE_TABLE}"

bronze_df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable(bronze_table)

print(f"✓ Bronze layer complete: {bronze_table}")

# COMMAND ----------

# DBTITLE 1,Verify Bronze Table

bronze_count = spark.table(bronze_table).count()
print(f"\n📊 Bronze Table Statistics:")
print(f"  Table: {bronze_table}")
print(f"  Total audio files: {bronze_count}")

if bronze_count == 0:
    print("\n⚠️ No audio files found. Please upload audio files to:")
    print(f"   {raw_audio_path}")
    dbutils.notebook.exit("No audio files to process. Exiting pipeline.")
else:
    display(spark.table(bronze_table).select("path", "length", "modificationTime").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥈 Silver Layer: Audio Transcription with Whisper
# MAGIC
# MAGIC Processes raw audio files to create transcribed text with metadata:
# MAGIC 1. Extract metadata from filename (call_id, agent_id, datetime)
# MAGIC 2. Transcribe audio using Whisper endpoint via `ai_query()` function
# MAGIC 3. Extract audio duration using mutagen
# MAGIC 4. Create clean, structured table for downstream analysis

# COMMAND ----------

# DBTITLE 1,Silver Layer - Audio Transcription

print(f"Transcribing audio using Whisper endpoint: {WHISPER_ENDPOINT_NAME}")

# Read from Bronze table (batch mode for better performance with small datasets)
silver_input_df = spark.table(bronze_table)

# Parse filename metadata (call_id, agent_id, call_datetime)
silver_input_df = parse_filename_metadata(silver_input_df)

# Transcribe audio using Whisper endpoint via ai_query()
# Note: ai_query() is used within selectExpr for SQL function access
silver_df = silver_input_df.selectExpr(
    "path",
    "file_name",
    "call_id",
    "agent_id",
    "call_datetime",
    "length as file_size_bytes",
    f"""ai_query(
        '{WHISPER_ENDPOINT_NAME}',
        content,
        returnType => 'STRING'
    ) as transcription"""
)

silver_df = silver_df.withColumn(
    "duration_seconds",
    F.round(F.col("file_size_bytes") / 16000, 0)  # Rough estimate: ~16KB per second for compressed audio
)

# Write to Silver table
silver_table = f"{CATALOG}.{SCHEMA}.{SILVER_TABLE}"

silver_df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable(silver_table)

print(f"✓ Silver layer complete: {silver_table}")

# COMMAND ----------

# DBTITLE 1,Verify Silver Table

silver_count = spark.table(silver_table).count()
print(f"\n📊 Silver Table Statistics:")
print(f"  Table: {silver_table}")
print(f"  Total transcribed calls: {silver_count}")

if silver_count > 0:
    display(spark.table(silver_table).select(
        "file_name", "call_id", "agent_id", "call_datetime",
        "duration_seconds", "transcription"
    ).limit(5))

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
print("LAKEFLOW SDP PIPELINE EXECUTION SUMMARY")
print("=" * 80)

bronze_cnt = spark.table(f"{CATALOG}.{SCHEMA}.{BRONZE_TABLE}").count()
silver_cnt = spark.table(f"{CATALOG}.{SCHEMA}.{SILVER_TABLE}").count()
gold_cnt = spark.table(f"{CATALOG}.{SCHEMA}.{GOLD_TABLE}").count()

print(f"\n📊 Record Counts:")
print(f"  Bronze (Raw Audio):       {bronze_cnt}")
print(f"  Silver (Transcriptions):  {silver_cnt}")
print(f"  Gold (AI Enriched):       {gold_cnt}")

print(f"\n✅ Tables Created:")
print(f"  1. {CATALOG}.{SCHEMA}.{BRONZE_TABLE}")
print(f"  2. {CATALOG}.{SCHEMA}.{SILVER_TABLE}")
print(f"  3. {CATALOG}.{SCHEMA}.{GOLD_TABLE}")

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
