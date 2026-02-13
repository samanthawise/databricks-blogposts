# Databricks notebook source
# MAGIC %md
# MAGIC # Prepare Data for Analytics Dashboard
# MAGIC
# MAGIC This notebook prepares aggregated metrics and trend data from the Gold table for
# MAGIC visualization in Databricks dashboards or BI tools.
# MAGIC
# MAGIC **Output Tables**:
# MAGIC - `dashboard_metrics`: Real-time metrics (call volume, sentiment, compliance)
# MAGIC - `dashboard_trends`: Time-series trends for visualization
# MAGIC - `dashboard_agent_performance`: Agent-level performance metrics
# MAGIC - `dashboard_call_reasons`: Call reason analysis
# MAGIC
# MAGIC **Dashboard Features**:
# MAGIC - Call volume trends over time
# MAGIC - Sentiment distribution
# MAGIC - Compliance score analysis
# MAGIC - Agent performance metrics
# MAGIC - Call reason breakdown
# MAGIC - Duration analysis

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Set Catalog and Schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Using: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Dashboard Metrics Table

# COMMAND ----------

# DBTITLE 1,Dashboard Metrics - Overall Statistics

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.{DASHBOARD_METRICS_TABLE}
AS
SELECT
    -- Overall metrics
    COUNT(*) as total_calls,
    COUNT(DISTINCT agent_id) as total_agents,
    COUNT(DISTINCT call_id) as unique_calls,

    -- Duration metrics
    ROUND(AVG(duration_seconds), 2) as avg_call_duration_sec,
    ROUND(MIN(duration_seconds), 2) as min_call_duration_sec,
    ROUND(MAX(duration_seconds), 2) as max_call_duration_sec,

    -- Sentiment distribution
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_sentiment_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_sentiment_count,
    SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_sentiment_count,
    SUM(CASE WHEN sentiment = 'mixed' THEN 1 ELSE 0 END) as mixed_sentiment_count,

    -- Compliance metrics
    ROUND(AVG(compliance_analysis.score), 2) as avg_compliance_score,
    ROUND(MIN(compliance_analysis.score), 2) as min_compliance_score,
    ROUND(MAX(compliance_analysis.score), 2) as max_compliance_score,
    SUM(CASE WHEN compliance_analysis.score < 70 THEN 1 ELSE 0 END) as low_compliance_calls,

    -- Call reasons (top 5)
    COLLECT_SET(classification) as all_call_reasons,

    -- Timestamp
    CURRENT_TIMESTAMP() as metrics_updated_at

FROM {CATALOG}.{SCHEMA}.{GOLD_TABLE}
""")

print(f"✓ Created: {CATALOG}.{SCHEMA}.{DASHBOARD_METRICS_TABLE}")

# Display metrics
display(spark.table(f"{CATALOG}.{SCHEMA}.{DASHBOARD_METRICS_TABLE}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Dashboard Trends Table

# COMMAND ----------

# DBTITLE 1,Dashboard Trends - Time Series Analysis

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.{DASHBOARD_TRENDS_TABLE}
AS
SELECT
    DATE(call_datetime) as call_date,
    HOUR(call_datetime) as call_hour,

    -- Call volume
    COUNT(*) as call_count,

    -- Duration
    ROUND(AVG(duration_seconds), 2) as avg_duration,

    -- Sentiment distribution
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
    SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count,

    -- Compliance
    ROUND(AVG(compliance_analysis.score), 2) as avg_compliance,

    -- Top call reason for this time period
    MODE(classification) as top_call_reason

FROM {CATALOG}.{SCHEMA}.{GOLD_TABLE}
GROUP BY DATE(call_datetime), HOUR(call_datetime)
ORDER BY call_date DESC, call_hour DESC
""")

print(f"✓ Created: {CATALOG}.{SCHEMA}.{DASHBOARD_TRENDS_TABLE}")

# Display sample trends
display(spark.table(f"{CATALOG}.{SCHEMA}.{DASHBOARD_TRENDS_TABLE}").limit(24))  # Last 24 hours

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Agent Performance Table

# COMMAND ----------

# DBTITLE 1,Dashboard - Agent Performance Metrics

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.dashboard_agent_performance
AS
SELECT
    agent_id,

    -- Call volume
    COUNT(*) as total_calls,

    -- Duration
    ROUND(AVG(duration_seconds), 2) as avg_call_duration,

    -- Sentiment
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_calls,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_calls,
    ROUND(100.0 * SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 2) as positive_percentage,

    -- Compliance
    ROUND(AVG(compliance_analysis.score), 2) as avg_compliance_score,
    SUM(CASE WHEN compliance_analysis.score < 70 THEN 1 ELSE 0 END) as low_compliance_calls,

    -- Call reasons handled
    COUNT(DISTINCT classification) as unique_call_reasons,

    -- Time range
    MIN(call_datetime) as first_call,
    MAX(call_datetime) as last_call,

    -- Performance tier
    CASE
        WHEN AVG(compliance_analysis.score) >= 90 THEN 'Excellent'
        WHEN AVG(compliance_analysis.score) >= 80 THEN 'Good'
        WHEN AVG(compliance_analysis.score) >= 70 THEN 'Average'
        ELSE 'Needs Improvement'
    END as performance_tier

FROM {CATALOG}.{SCHEMA}.{GOLD_TABLE}
GROUP BY agent_id
ORDER BY avg_compliance_score DESC, total_calls DESC
""")

print(f"✓ Created: {CATALOG}.{SCHEMA}.dashboard_agent_performance")

# Display agent performance
display(spark.table(f"{CATALOG}.{SCHEMA}.dashboard_agent_performance"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Call Reasons Analysis Table

# COMMAND ----------

# DBTITLE 1,Dashboard - Call Reasons Breakdown

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.dashboard_call_reasons
AS
SELECT
    classification as call_reason,

    -- Volume
    COUNT(*) as call_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage_of_total,

    -- Duration
    ROUND(AVG(duration_seconds), 2) as avg_duration,

    -- Sentiment distribution
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
    SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
    ROUND(100.0 * SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 2) as negative_percentage,

    -- Compliance
    ROUND(AVG(compliance_analysis.score), 2) as avg_compliance_score,

    -- Complexity indicators
    ROUND(AVG(duration_seconds), 2) as avg_handle_time,
    SUM(CASE WHEN compliance_analysis.score < 70 THEN 1 ELSE 0 END) as compliance_issues

FROM {CATALOG}.{SCHEMA}.{GOLD_TABLE}
GROUP BY classification
ORDER BY call_count DESC
""")

print(f"✓ Created: {CATALOG}.{SCHEMA}.dashboard_call_reasons")

# Display call reasons
display(spark.table(f"{CATALOG}.{SCHEMA}.dashboard_call_reasons"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Compliance Violations Analysis

# COMMAND ----------

# DBTITLE 1,Dashboard - Compliance Issues Breakdown

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.dashboard_compliance_issues
AS
SELECT
    -- Overall compliance
    CASE
        WHEN compliance_analysis.score >= 90 THEN '90-100: Excellent'
        WHEN compliance_analysis.score >= 80 THEN '80-89: Good'
        WHEN compliance_analysis.score >= 70 THEN '70-79: Average'
        WHEN compliance_analysis.score >= 60 THEN '60-69: Below Average'
        ELSE '0-59: Poor'
    END as compliance_range,

    COUNT(*) as call_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,

    -- Average metrics for this range
    ROUND(AVG(compliance_analysis.score), 2) as avg_score,
    ROUND(AVG(duration_seconds), 2) as avg_duration,

    -- Sentiment correlation
    ROUND(100.0 * SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 2) as negative_sentiment_pct

FROM {CATALOG}.{SCHEMA}.{GOLD_TABLE}
GROUP BY
    CASE
        WHEN compliance_analysis.score >= 90 THEN '90-100: Excellent'
        WHEN compliance_analysis.score >= 80 THEN '80-89: Good'
        WHEN compliance_analysis.score >= 70 THEN '70-79: Average'
        WHEN compliance_analysis.score >= 60 THEN '60-69: Below Average'
        ELSE '0-59: Poor'
    END
ORDER BY avg_score DESC
""")

print(f"✓ Created: {CATALOG}.{SCHEMA}.dashboard_compliance_issues")

# Display compliance analysis
display(spark.table(f"{CATALOG}.{SCHEMA}.dashboard_compliance_issues"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dashboard Data Summary

# COMMAND ----------

# DBTITLE 1,Dashboard Preparation Complete

print("\n" + "=" * 80)
print("DASHBOARD DATA PREPARATION COMPLETE")
print("=" * 80)

# Get row counts
metrics_count = spark.table(f"{CATALOG}.{SCHEMA}.{DASHBOARD_METRICS_TABLE}").count()
trends_count = spark.table(f"{CATALOG}.{SCHEMA}.{DASHBOARD_TRENDS_TABLE}").count()
agent_count = spark.table(f"{CATALOG}.{SCHEMA}.dashboard_agent_performance").count()
reasons_count = spark.table(f"{CATALOG}.{SCHEMA}.dashboard_call_reasons").count()
compliance_count = spark.table(f"{CATALOG}.{SCHEMA}.dashboard_compliance_issues").count()

print(f"\n✓ Dashboard Tables Created:")
print(f"  1. {DASHBOARD_METRICS_TABLE} ({metrics_count} record)")
print(f"  2. {DASHBOARD_TRENDS_TABLE} ({trends_count} time periods)")
print(f"  3. dashboard_agent_performance ({agent_count} agents)")
print(f"  4. dashboard_call_reasons ({reasons_count} reasons)")
print(f"  5. dashboard_compliance_issues ({compliance_count} ranges)")

print(f"\n📊 Ready for Dashboarding:")
print(f"  - Create Databricks Dashboard")
print(f"  - Connect to BI tools (Tableau, Power BI, etc.)")
print(f"  - Build custom visualizations")

print(f"\n🔄 Refresh Frequency:")
print(f"  - Run this notebook after pipeline execution")
print(f"  - Schedule for periodic refresh (e.g., hourly, daily)")
print(f"  - Can be triggered by pipeline completion")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Dashboard Queries

# COMMAND ----------

# DBTITLE 1,Sample Query - Call Volume by Hour

# MAGIC %sql
# MAGIC SELECT
# MAGIC     call_date,
# MAGIC     call_hour,
# MAGIC     call_count,
# MAGIC     avg_compliance
# MAGIC FROM dashboard_trends
# MAGIC ORDER BY call_date DESC, call_hour DESC
# MAGIC LIMIT 24

# COMMAND ----------

# DBTITLE 1,Sample Query - Top Performing Agents

# MAGIC %sql
# MAGIC SELECT
# MAGIC     agent_id,
# MAGIC     total_calls,
# MAGIC     positive_percentage,
# MAGIC     avg_compliance_score,
# MAGIC     performance_tier
# MAGIC FROM dashboard_agent_performance
# MAGIC WHERE total_calls >= 5  -- Agents with at least 5 calls
# MAGIC ORDER BY avg_compliance_score DESC
# MAGIC LIMIT 10

# COMMAND ----------

# DBTITLE 1,Sample Query - Call Reason Distribution

# MAGIC %sql
# MAGIC SELECT
# MAGIC     call_reason,
# MAGIC     call_count,
# MAGIC     percentage_of_total,
# MAGIC     avg_compliance_score,
# MAGIC     negative_percentage
# MAGIC FROM dashboard_call_reasons
# MAGIC ORDER BY call_count DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC ### Build Databricks Dashboard
# MAGIC 1. Go to "Dashboards" in Databricks UI
# MAGIC 2. Create new dashboard
# MAGIC 3. Add visualizations using the tables created above
# MAGIC 4. Example widgets:
# MAGIC    - Line chart: Call volume over time
# MAGIC    - Pie chart: Sentiment distribution
# MAGIC    - Bar chart: Agent performance comparison
# MAGIC    - KPI cards: Total calls, average compliance, etc.
# MAGIC
# MAGIC ### Dashboard Refresh Schedule
# MAGIC - Set up a job to run this notebook periodically
# MAGIC - Trigger after pipeline execution
# MAGIC - Use Delta table streaming for real-time updates
# MAGIC
# MAGIC ### Export to BI Tools
# MAGIC - Connect Tableau/Power BI to these tables via JDBC/ODBC
# MAGIC - Use Databricks SQL endpoint for optimal performance
# MAGIC - Leverage Delta caching for fast query responses
