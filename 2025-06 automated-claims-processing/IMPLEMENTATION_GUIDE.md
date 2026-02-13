# 📖 Implementation Guide
## AI-Powered Call Center Analytics - Step-by-Step Setup

This guide provides detailed instructions for deploying the AI-Powered Call Center Analytics solution accelerator from scratch.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Foundation & Endpoint Setup](#phase-1-foundation--endpoint-setup)
3. [Phase 2: Core Pipeline Deployment](#phase-2-core-pipeline-deployment)
4. [Phase 3: Agent Integration Setup](#phase-3-agent-integration-setup)
5. [Phase 4: Dashboard & Analytics](#phase-4-dashboard--analytics)
6. [Verification & Testing](#verification--testing)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

---

## Prerequisites

### Databricks Workspace Requirements

- ✅ **Databricks Workspace** (AWS, Azure, or GCP)
- ✅ **Unity Catalog** enabled
- ✅ **Model Serving** permissions
- ✅ **Foundation Model** endpoints access (Claude, Llama)
- ✅ **GPU Quota** for Whisper endpoint (GPU_MEDIUM or GPU_LARGE)

### User Permissions Required

```yaml
Workspace Level:
  - Can attach clusters
  - Can create clusters
  - Can create Model Serving endpoints

Unity Catalog Level:
  - CREATE CATALOG (or access to existing catalog)
  - CREATE SCHEMA
  - CREATE VOLUME
  - CREATE TABLE
  - CREATE FUNCTION
```

### Recommended Cluster Configuration

```yaml
Runtime: 14.3 LTS or later
Node Type: i3.xlarge (4 cores, 30.5 GB RAM)
Workers: 1-4 (autoscaling)
Photon: Enabled
```

---

## Phase 1: Foundation & Endpoint Setup

**Estimated Time:** 30-45 minutes (including Whisper endpoint deployment)

### Step 1.1: Import Notebooks

1. Download or clone this repository
2. In Databricks workspace, navigate to **Workspace** → **Users** → **[Your Username]**
3. Right-click and select **Import**
4. Upload the entire `2025-06 automated-claims-processing` directory

### Step 1.2: Configure the Solution

1. Open `config/config.py`
2. Update the widget default values (or use defaults):

```python
# Configuration widgets (can be changed at runtime)
CATALOG = "call_center_analytics"      # Your Unity Catalog catalog
SCHEMA = "main"                         # Schema name
VOLUME = "call_center_data"             # Volume name
ENVIRONMENT = "dev"                     # Environment: dev, prod, demo
```

3. **DO NOT** change endpoint names unless you have specific requirements:
   - `WHISPER_ENDPOINT_NAME = "whisper-v3-large-pytorch"`
   - `LLM_ENDPOINT_REASONING = "databricks-claude-sonnet-4-5"`
   - `LLM_ENDPOINT_FAST = "databricks-gpt-5-nano"`

### Step 1.3: Initialize Environment

1. Open notebook: `setup/00-setup.py`
2. Attach to your cluster
3. **Run All Cells**

**What This Does:**
- Creates Unity Catalog catalog, schema, and volumes
- Creates lookup tables (`call_reasons`, `compliance_guidelines`)
- Sets up volume directory structure
- Verifies Foundation Model endpoints are accessible

**Expected Output:**
```
✓ Created catalog: call_center_analytics
✓ Using schema: main
✓ Created volume: call_center_data
✓ Created table: call_reasons (18 reasons)
✓ Created table: compliance_guidelines (10 guidelines)
✓ All Foundation Model endpoints are available!
```

**If Errors Occur:**
- **Catalog Exists Error**: Set widget `reset_all_data = false` or use existing catalog
- **Permissions Error**: Contact workspace admin for Unity Catalog permissions
- **Endpoint Not Found**: Verify Foundation Model endpoints are enabled in workspace

### Step 1.4: Deploy Whisper Endpoint

1. Open notebook: `setup/01-deploy-whisper-endpoint.py`
2. **Run All Cells**

**What This Does:**
- Deploys PyTorch Whisper v3 Large model to Model Serving
- Configures GPU compute (GPU_MEDIUM for AWS, GPU_LARGE for Azure)
- Enables scale-to-zero for cost optimization
- Waits for endpoint to be ready
- Tests endpoint with sample audio (if available)

**Expected Duration:** 10-15 minutes for initial deployment

**Expected Output:**
```
Deploying Whisper endpoint: whisper-v3-large-pytorch
This may take 10-15 minutes...
✓ Endpoint 'whisper-v3-large-pytorch' deployed successfully!
✓ Endpoint 'whisper-v3-large-pytorch' is ready for inference!
```

**If Errors Occur:**
- **GPU Quota Error**: Request GPU quota increase from cloud provider
- **Timeout Error**: Wait longer (up to 30 minutes) or check endpoint status manually
- **Already Exists**: Widget `action = use_existing` to skip deployment

### Step 1.5: (Optional) Generate Demo Data

1. Open notebook: `setup/sample_data_generator.py`
2. **Run All Cells**

**What This Does:**
- Generates 50 synthetic call scenarios
- Creates realistic call transcripts
- Generates placeholder audio files
- Saves to `synthetic_call_data` table

**Expected Output:**
```
✓ Generated 50 synthetic call records
✓ Created 50 placeholder audio files
✓ Saved synthetic call data to table
```

**Skip This Step If:**
- You have real audio files to process
- You want to upload your own audio data

---

## Phase 2: Core Pipeline Deployment

**Estimated Time:** 15-30 minutes (depends on audio file count)

### Step 2.1: Upload Audio Files (If Using Real Data)

1. Navigate to **Catalog** → **[Your Catalog]** → **[Your Schema]** → **Volumes** → **call_center_data**
2. Open the **raw_recordings** directory
3. Upload audio files (WAV, MP3, or FLAC format)

**Audio File Naming Convention:**
```
{call_id}_{agent_id}_{YYYY-MM-DD_HH-MM-SS}.{ext}

Examples:
  ABC123_AGT001_2024-01-15_10-30-45.wav
  XYZ789_AGT002_2024-02-20_14-22-10.mp3
```

**If File Names Don't Match Pattern:**
- Files will still be ingested
- Metadata parsing may fail (call_id, agent_id, datetime)
- Manual metadata enrichment required post-processing

### Step 2.2: Run Lakeflow SDP Pipeline

1. Open notebook: `pipeline/02-sdp-bronze-silver-gold.py`
2. **Run All Cells**

**What This Does:**

**Bronze Layer (Auto Loader):**
- Incrementally ingests audio files from volume
- Creates `raw_audio_files` table
- Checkpoint-based exactly-once processing

**Silver Layer (Transcription):**
- Parses filename metadata (call_id, agent_id, datetime)
- Transcribes audio using Whisper endpoint via `ai_query()`
- Extracts audio duration
- Creates `transcriptions_silver` table

**Gold Layer (AI Enrichment):**
- Applies comprehensive AI analysis:
  - Sentiment analysis
  - Call summarization
  - Dynamic classification (from lookup table)
  - Named entity recognition (person, policy, date, phone, email)
  - PII masking
  - Compliance scoring (with violations)
  - Follow-up email generation (structured JSON)
- Creates `call_analysis_gold` table

**Expected Duration:**
- Bronze: 1-5 minutes
- Silver: 5-15 minutes (depends on audio count and duration)
- Gold: 5-10 minutes (AI Functions processing)

**Expected Output:**
```
✓ Bronze layer complete: raw_audio_files
📊 Bronze Table: 50 audio files

✓ Silver layer complete: transcriptions_silver
📊 Silver Table: 50 transcribed calls

✓ Intermediate Gold layer complete
✓ Final Gold layer complete: call_analysis_gold
📊 Gold Table: 50 enriched calls

✓ Pipeline complete: Bronze → Silver → Gold
```

**Sample Gold Table Query:**
```sql
SELECT
    call_id,
    agent_id,
    sentiment,
    summary,
    classification,
    compliance_analysis.score as compliance_score,
    follow_up_email.subject
FROM call_center_analytics.main.call_analysis_gold
LIMIT 10;
```

**If Errors Occur:**
- **No Audio Files**: Upload audio or run sample data generator
- **Whisper Endpoint Error**: Verify endpoint is in "Ready" state
- **AI Function Error**: Check Foundation Model endpoint access
- **Transcription Empty**: Verify audio file format and content

---

## Phase 3: Agent Integration Setup

**Estimated Time:** 5-10 minutes

### Step 3.1: Create Unity Catalog Functions

1. Open notebook: `tools/03-create-uc-tools.py`
2. **Run All Cells**

**What This Does:**
- Creates 8 SQL-based UC Functions:
  1. `get_customer_policy_profile_by_phone_number(phone)`
  2. `get_customer_sentiment_by_phone_number(phone)`
  3. `get_customer_transcript_by_phone_number(phone)`
  4. `get_call_summary_by_phone_number(phone)`
  5. `get_compliance_score_by_phone_number(phone)`
  6. `get_follow_up_email_by_phone_number(phone)`
  7. `get_call_history_by_phone_number(phone, limit_count)`
  8. `search_calls_by_classification(call_reason, limit_count)`

**Expected Output:**
```
✓ Created: get_customer_policy_profile_by_phone_number()
✓ Created: get_customer_sentiment_by_phone_number()
✓ Created: get_customer_transcript_by_phone_number()
✓ Created: get_call_summary_by_phone_number()
✓ Created: get_compliance_score_by_phone_number()
✓ Created: get_follow_up_email_by_phone_number()
✓ Created: get_call_history_by_phone_number()
✓ Created: search_calls_by_classification()

Total UC Functions: 8
```

**Test UC Functions:**
```sql
-- Test with a phone number from your data
SELECT get_customer_sentiment_by_phone_number('(555)-123-4567');
SELECT * FROM get_call_history_by_phone_number('(555)-123-4567', 5);
```

### Step 3.2: Test Mock Agent Endpoints

1. Open notebook: `agents_mock/04-mock-agent-endpoints.py`
2. **Run All Cells**

**What This Does:**
- Creates mock agent classes for testing:
  - MockCustomerServiceAgent
  - MockPolicyQAAgent
  - MockComplianceAgent
  - MockSupervisorAgent
- Demonstrates agent integration patterns
- Documents Agent Bricks integration requirements

**Expected Output:**
```
Mock Agent Response:
agent: Customer Service Agent
response: Thank you for contacting VitalGuard Insurance...
mock: True

Mock Customer Context:
phone_number: (555)-123-4567
profile: Mock Customer Profile
sentiment: Neutral
mock: True
```

**Note:** These are placeholder agents for testing. Production agents will be handled by the external Agent Bricks Knowledge Assistant system, which manages all orchestration and agentic workflows.

---

## Phase 4: Dashboard & Analytics

**Estimated Time:** 5-10 minutes

### Step 4.1: Prepare Dashboard Data

1. Open notebook: `notebooks/05-prepare-dashboard-data.py`
2. **Run All Cells**

**What This Does:**
- Creates aggregated dashboard tables:
  - `dashboard_metrics`: Overall statistics
  - `dashboard_trends`: Time-series trends (hourly)
  - `dashboard_agent_performance`: Agent-level metrics
  - `dashboard_call_reasons`: Call reason analysis
  - `dashboard_compliance_issues`: Compliance distribution

**Expected Output:**
```
✓ Created: dashboard_metrics (1 record)
✓ Created: dashboard_trends (24 time periods)
✓ Created: dashboard_agent_performance (5 agents)
✓ Created: dashboard_call_reasons (18 reasons)
✓ Created: dashboard_compliance_issues (5 ranges)
```

### Step 4.2: Build Databricks Dashboard

1. Navigate to **Dashboards** in Databricks UI
2. Click **Create Dashboard**
3. Name it: "Call Center Analytics Dashboard"
4. Add visualizations:

**Recommended Widgets:**

**KPI Cards:**
- Total Calls: `SELECT total_calls FROM dashboard_metrics`
- Average Compliance: `SELECT avg_compliance_score FROM dashboard_metrics`
- Positive Sentiment %: `SELECT ROUND(100.0 * positive_sentiment_count / total_calls, 2) FROM dashboard_metrics`

**Line Chart - Call Volume Trend:**
```sql
SELECT call_date, call_hour, call_count
FROM dashboard_trends
ORDER BY call_date, call_hour
```

**Pie Chart - Sentiment Distribution:**
```sql
SELECT
    'Positive' as sentiment, positive_sentiment_count as count
FROM dashboard_metrics
UNION ALL
SELECT 'Negative', negative_sentiment_count FROM dashboard_metrics
UNION ALL
SELECT 'Neutral', neutral_sentiment_count FROM dashboard_metrics
```

**Bar Chart - Top Call Reasons:**
```sql
SELECT call_reason, call_count
FROM dashboard_call_reasons
ORDER BY call_count DESC
LIMIT 10
```

**Bar Chart - Agent Performance:**
```sql
SELECT agent_id, avg_compliance_score, total_calls
FROM dashboard_agent_performance
ORDER BY avg_compliance_score DESC
```

5. Set dashboard refresh schedule (e.g., hourly)

---

## Verification & Testing

### End-to-End Verification Checklist

- [ ] **Bronze Table**: Audio files ingested
- [ ] **Silver Table**: Transcriptions generated
- [ ] **Gold Table**: AI enrichments applied
- [ ] **UC Functions**: Created and testable
- [ ] **Dashboard Tables**: Populated with metrics
- [ ] **Dashboard**: Built and rendering

### Detailed Verification Queries

**1. Verify Bronze Layer:**
```sql
SELECT COUNT(*) as total_files FROM call_center_analytics.main.raw_audio_files;
```

**2. Verify Silver Layer:**
```sql
SELECT
    call_id,
    agent_id,
    LENGTH(transcription) as transcript_length,
    duration_seconds
FROM call_center_analytics.main.transcriptions_silver
LIMIT 5;
```

**3. Verify Gold Layer - AI Enrichments:**
```sql
SELECT
    call_id,
    sentiment,
    classification,
    compliance_analysis.score as compliance_score,
    CASE
        WHEN LENGTH(summary) > 0 THEN 'Yes'
        ELSE 'No'
    END as has_summary,
    CASE
        WHEN follow_up_email.subject IS NOT NULL THEN 'Yes'
        ELSE 'No'
    END as has_email
FROM call_center_analytics.main.call_analysis_gold
LIMIT 5;
```

**4. Test UC Functions:**
```sql
-- Get a sample phone number from Gold table
SELECT DISTINCT phone_numbers[0] as phone
FROM call_center_analytics.main.call_analysis_gold
WHERE SIZE(phone_numbers) > 0
LIMIT 1;

-- Test with that phone number
SELECT get_customer_sentiment_by_phone_number('<phone-from-above>');
```

**5. Verify Dashboard Data:**
```sql
SELECT * FROM call_center_analytics.main.dashboard_metrics;
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Whisper Endpoint Not Ready

**Symptoms:**
- Silver layer fails with endpoint error
- `ai_query()` returns empty or error

**Solutions:**
1. Check endpoint status:
   ```python
   from databricks.sdk import WorkspaceClient
   w = WorkspaceClient()
   endpoint = w.serving_endpoints.get("whisper-v3-large-pytorch")
   print(endpoint.state)
   ```
2. Wait for endpoint to reach "READY" state (can take 15-30 min)
3. Restart endpoint if stuck:
   ```python
   w.serving_endpoints.delete("whisper-v3-large-pytorch")
   # Re-run 01-deploy-whisper-endpoint.py
   ```

#### Issue 2: AI Functions Failing

**Symptoms:**
- Gold layer errors on `ai_query()`, `ai_classify()`, etc.
- "Endpoint not found" or "Access denied" errors

**Solutions:**
1. Verify Foundation Model access:
   ```sql
   SELECT ai_analyze_sentiment('This is a test');
   ```
2. Check workspace Foundation Model settings
3. Contact workspace admin to enable Foundation Models

#### Issue 3: Empty Transcriptions

**Symptoms:**
- Silver table has records but `transcription` column is empty
- No errors in pipeline

**Solutions:**
1. Verify audio file format (use WAV, MP3, or FLAC)
2. Check audio file content (not corrupted)
3. Test Whisper endpoint manually:
   ```sql
   SELECT ai_query('whisper-v3-large-pytorch', <binary-content>);
   ```
4. Check Whisper endpoint logs for errors

#### Issue 4: UC Functions Not Found

**Symptoms:**
- `FUNCTION_NOT_FOUND` error when calling UC Functions

**Solutions:**
1. Verify functions exist:
   ```sql
   SHOW USER FUNCTIONS IN call_center_analytics.main;
   ```
2. Re-run `tools/03-create-uc-tools.py`
3. Check catalog/schema spelling in queries

#### Issue 5: Dashboard Data Empty

**Symptoms:**
- Dashboard tables created but have 0 rows

**Solutions:**
1. Verify Gold table has data:
   ```sql
   SELECT COUNT(*) FROM call_center_analytics.main.call_analysis_gold;
   ```
2. If Gold table empty, re-run pipeline: `pipeline/02-sdp-bronze-silver-gold.py`
3. Re-run dashboard prep: `notebooks/05-prepare-dashboard-data.py`

---

## Production Deployment

### Workflow Orchestration

1. **Create Lakeflow Workflow:**
   - Use `config/pipeline_config.yaml` as template
   - Customize cluster configuration for production
   - Set up file arrival trigger for `raw_recordings` volume

2. **Configure Alerts:**
   - Workflow failure notifications
   - Compliance score threshold alerts
   - Endpoint health monitoring

3. **Schedule Maintenance:**
   - Daily pipeline runs (if batch processing)
   - Weekly dashboard refresh
   - Monthly lookup table updates

### Performance Optimization

**For Large-Scale Deployments:**

1. **Cluster Scaling:**
   - Increase worker count (4-8 workers)
   - Use larger node types (i3.2xlarge)
   - Enable cluster autoscaling

2. **Whisper Endpoint:**
   - Increase endpoint size (Medium or Large)
   - Disable scale-to-zero for 24/7 availability
   - Monitor inference latency

3. **Pipeline Optimization:**
   - Partition Gold table by `call_date`
   - Enable Z-ORDER on frequently queried columns
   - Use Delta caching for dashboard queries

### Security Hardening

1. **Access Control:**
   - Restrict catalog/schema access to authorized users
   - Use UC Function grants for agent access
   - Enable audit logging

2. **Data Protection:**
   - Ensure PII masking is enabled
   - Review and customize compliance guidelines
   - Encrypt sensitive columns

3. **Endpoint Security:**
   - Enable endpoint authentication
   - Use private networking for Model Serving
   - Rotate endpoint tokens regularly

---

## Next Steps

After successful deployment:

1. **Integrate Agent Bricks:**
   - Register UC Functions with Agent Bricks
   - Agent Bricks will handle all orchestration and workflows
   - Deploy Customer Service Agent

2. **Customize for Your Use Case:**
   - Add custom call reasons to lookup table
   - Extend compliance guidelines
   - Modify AI prompts and schemas

3. **Scale to Production:**
   - Increase cluster size and endpoint capacity
   - Set up monitoring and alerting
   - Configure automated testing

4. **Expand Capabilities:**
   - Add Vector Search for policy documents
   - Implement real-time streaming
   - Build custom agent workflows

---

## Support & Resources

- **Documentation**: [README.md](./README.md)
- **Databricks Docs**: https://docs.databricks.com
- **Community**: https://community.databricks.com
- **Support**: Contact your Databricks account team

---

**Implementation Time Estimate:**
- **Phase 1**: 30-45 minutes
- **Phase 2**: 15-30 minutes
- **Phase 3**: 5-10 minutes
- **Phase 4**: 5-10 minutes
- **Total**: ~1-1.5 hours (excluding Whisper endpoint deployment time)

Good luck with your implementation! 🚀
