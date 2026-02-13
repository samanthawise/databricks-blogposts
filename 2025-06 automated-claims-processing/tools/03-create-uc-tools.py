# Databricks notebook source
# MAGIC %md
# MAGIC # Create Unity Catalog Functions for Agent Integration
# MAGIC
# MAGIC This notebook creates SQL-based UC Functions that provide a clean interface for external agents
# MAGIC (Agent Bricks or other agent systems) to access call center data.
# MAGIC
# MAGIC **Purpose**: Enable agent systems to retrieve customer information, sentiment, transcripts, summaries,
# MAGIC and compliance scores without direct table access.
# MAGIC
# MAGIC **Security**: UC Functions provide:
# MAGIC - Fine-grained access control
# MAGIC - Audit logging
# MAGIC - Data governance via Unity Catalog
# MAGIC
# MAGIC **Agent Bricks Integration**: These functions are designed to be used by the external Agent Bricks
# MAGIC Knowledge Assistant system for multi-agent workflows.

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Setup Widget for Function Recreation
dbutils.widgets.dropdown("recreate_uc_tools", "false", ["false", "true"], "Recreate UC Tools")

recreate_uc_tools = dbutils.widgets.get("recreate_uc_tools") == "true"
print(f"Recreate UC Tools: {recreate_uc_tools}")

# COMMAND ----------

# DBTITLE 1,List Existing UC Functions

def show_or_clean_uc_tools(catalog: str, schema: str, delete_functions: bool = False):
    """
    List or clean up existing UC functions in the schema.

    Args:
        catalog: Catalog name
        schema: Schema name
        delete_functions: If True, drop all existing user functions
    """
    df = spark.sql(f"SHOW USER FUNCTIONS IN {catalog}.{schema}")
    count = df.count()
    rows = df.collect()
    functions = [r.function for r in rows]

    print(f"Found {count} user-defined UC functions:")
    for func in functions:
        print(f"  - {func}")

    if count > 0 and delete_functions:
        print(f"\n⚠️  Dropping {count} existing functions...")
        for function_name in functions:
            spark.sql(f"DROP FUNCTION IF EXISTS {function_name}")
            print(f"  ✓ Dropped {function_name}")

        remaining = spark.sql(f"SHOW USER FUNCTIONS IN {catalog}.{schema}").count()
        print(f"\n✓ {remaining} functions remaining")

# Set catalog and schema context
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

show_or_clean_uc_tools(CATALOG, SCHEMA, delete_functions=recreate_uc_tools)

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 1: Get Customer Profile by Phone Number
# MAGIC
# MAGIC Returns a comprehensive customer profile including:
# MAGIC - Customer name and contact information
# MAGIC - Policy number
# MAGIC - Latest call information

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_customer_policy_profile_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Return customer policy profile for a given phone number from the latest call'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT
# MAGIC     CONCAT(
# MAGIC       'Customer Profile: ',
# MAGIC       COALESCE(customer_name, 'Name not available'), ' | ',
# MAGIC       'Phone: ', phone, ' | ',
# MAGIC       'Policy Number: ', COALESCE(policy_number_extracted, 'Not found'), ' | ',
# MAGIC       'Last Call: ', DATE_FORMAT(call_datetime, 'yyyy-MM-dd HH:mm:ss'), ' | ',
# MAGIC       'Agent: ', agent_id, ' | ',
# MAGIC       'Call Reason: ', classification
# MAGIC     ) as profile
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 1
# Test with a sample phone number (adjust based on your data)
# %sql
# SELECT get_customer_policy_profile_by_phone_number('(555)-123-4567') as profile

print("✓ Created: get_customer_policy_profile_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 2: Get Customer Sentiment by Phone Number
# MAGIC
# MAGIC Returns the sentiment from the customer's most recent call

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_customer_sentiment_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Return customer sentiment from the most recent call for a given phone number'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT sentiment
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 2
print("✓ Created: get_customer_sentiment_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 3: Get Customer Transcript by Phone Number
# MAGIC
# MAGIC Returns the full transcript from the customer's most recent call

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_customer_transcript_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Return the full call transcript from the most recent call for a given phone number'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT transcription
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 3
print("✓ Created: get_customer_transcript_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 4: Get Call Summary by Phone Number
# MAGIC
# MAGIC Returns the AI-generated summary from the customer's most recent call

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_call_summary_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Return AI-generated call summary from the most recent call for a given phone number'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT summary
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 4
print("✓ Created: get_call_summary_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 5: Get Compliance Score by Phone Number
# MAGIC
# MAGIC Returns compliance analysis from the customer's most recent call

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_compliance_score_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRUCT<score: INT, violations: ARRAY<STRING>, recommendations: STRING>
# MAGIC COMMENT 'Return compliance analysis (score, violations, recommendations) from the most recent call'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT compliance_analysis
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 5
print("✓ Created: get_compliance_score_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 6: Get Follow-up Email by Phone Number
# MAGIC
# MAGIC Returns the AI-generated follow-up email from the customer's most recent call

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_follow_up_email_by_phone_number(
# MAGIC   phone STRING
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC COMMENT 'Return AI-generated follow-up email JSON from the most recent call'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT TO_JSON(follow_up_email)
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 6
print("✓ Created: get_follow_up_email_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 7: Get Call History by Phone Number
# MAGIC
# MAGIC Returns call history for a customer (last N calls)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION get_call_history_by_phone_number(
# MAGIC   phone STRING,
# MAGIC   limit_count INT
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   call_id STRING,
# MAGIC   call_datetime TIMESTAMP,
# MAGIC   agent_id STRING,
# MAGIC   classification STRING,
# MAGIC   sentiment STRING,
# MAGIC   summary STRING,
# MAGIC   duration_seconds DOUBLE
# MAGIC )
# MAGIC COMMENT 'Return call history (last N calls) for a given phone number'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT
# MAGIC     call_id,
# MAGIC     call_datetime,
# MAGIC     agent_id,
# MAGIC     classification,
# MAGIC     sentiment,
# MAGIC     summary,
# MAGIC     duration_seconds
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE ARRAY_CONTAINS(phone_numbers, phone)
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT limit_count
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 7
# %sql
# SELECT * FROM get_call_history_by_phone_number('(555)-123-4567', 5)

print("✓ Created: get_call_history_by_phone_number()")

# COMMAND ----------

# MAGIC %md
# MAGIC ## UC Function 8: Search Calls by Classification
# MAGIC
# MAGIC Find calls matching a specific classification/reason

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION search_calls_by_classification(
# MAGIC   call_reason STRING,
# MAGIC   limit_count INT
# MAGIC )
# MAGIC RETURNS TABLE (
# MAGIC   call_id STRING,
# MAGIC   call_datetime TIMESTAMP,
# MAGIC   customer_name STRING,
# MAGIC   agent_id STRING,
# MAGIC   sentiment STRING,
# MAGIC   summary STRING,
# MAGIC   compliance_score INT
# MAGIC )
# MAGIC COMMENT 'Search calls by classification/call reason (e.g., "Claim status inquiry")'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT
# MAGIC     call_id,
# MAGIC     call_datetime,
# MAGIC     customer_name,
# MAGIC     agent_id,
# MAGIC     sentiment,
# MAGIC     summary,
# MAGIC     compliance_analysis.score as compliance_score
# MAGIC   FROM call_analysis_gold
# MAGIC   WHERE classification = call_reason
# MAGIC   ORDER BY call_datetime DESC
# MAGIC   LIMIT limit_count
# MAGIC );

# COMMAND ----------

# DBTITLE 1,Test Function 8
print("✓ Created: search_calls_by_classification()")

# COMMAND ----------

# DBTITLE 1,List All Created UC Functions

print("\n" + "=" * 80)
print("UC FUNCTIONS CREATED SUCCESSFULLY")
print("=" * 80)

df_functions = spark.sql(f"SHOW USER FUNCTIONS IN {CATALOG}.{SCHEMA}")
functions_list = [row.function for row in df_functions.collect()]

print(f"\nTotal UC Functions: {len(functions_list)}")
print("\nAvailable Functions:")
for i, func in enumerate(functions_list, 1):
    print(f"  {i}. {func}")

print("\n" + "=" * 80)
print("USAGE FOR AGENT BRICKS INTEGRATION")
print("=" * 80)
print("""
These UC Functions can be registered with Agent Bricks for use in multi-agent workflows.

Example agent tool registration:
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Register UC Function as agent tool
tool = w.agent_tools.create(
    name="get_customer_sentiment",
    function_name=f"{catalog}.{schema}.get_customer_sentiment_by_phone_number",
    description="Retrieve customer sentiment from most recent call"
)
```

Example agent usage in LangGraph:
```python
from langgraph.prebuilt import ToolNode

# Define tools for agent
tools = [
    get_customer_policy_profile_by_phone_number,
    get_customer_sentiment_by_phone_number,
    get_call_summary_by_phone_number,
    get_compliance_score_by_phone_number
]

# Create tool node for agent
tool_node = ToolNode(tools)
```
""")
print("=" * 80)

# COMMAND ----------

# DBTITLE 1,Generate Function Documentation

print("\n" + "=" * 80)
print("FUNCTION REFERENCE")
print("=" * 80)

function_docs = {
    "get_customer_policy_profile_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRING",
        "description": "Get comprehensive customer profile from latest call"
    },
    "get_customer_sentiment_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRING",
        "description": "Get customer sentiment from latest call"
    },
    "get_customer_transcript_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRING",
        "description": "Get full call transcript from latest call"
    },
    "get_call_summary_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRING",
        "description": "Get AI-generated summary from latest call"
    },
    "get_compliance_score_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRUCT<score: INT, violations: ARRAY, recommendations: STRING>",
        "description": "Get compliance analysis from latest call"
    },
    "get_follow_up_email_by_phone_number": {
        "params": "phone: STRING",
        "returns": "STRING (JSON)",
        "description": "Get AI-generated follow-up email"
    },
    "get_call_history_by_phone_number": {
        "params": "phone: STRING, limit_count: INT",
        "returns": "TABLE",
        "description": "Get call history for customer (last N calls)"
    },
    "search_calls_by_classification": {
        "params": "call_reason: STRING, limit_count: INT",
        "returns": "TABLE",
        "description": "Search calls by classification/reason"
    }
}

for func_name, doc in function_docs.items():
    print(f"\n{func_name}({doc['params']})")
    print(f"  Returns: {doc['returns']}")
    print(f"  Description: {doc['description']}")

print("\n" + "=" * 80)
