# 🧠 AI-Powered Call Center Analytics – Unified Solution Accelerator

A comprehensive Databricks solution accelerator that transforms call center audio recordings into actionable insights using **Lakeflow Spark Declarative Pipelines (SDP)**, **Whisper transcription**, **AI Functions**, and **Agent Bricks integration**.

This unified solution combines the best patterns from two prior accelerators:
- **Excellent documentation and customer-ready packaging**
- **Production-grade Whisper endpoint transcription**
- **Comprehensive batch AI analysis**
- **Agent integration readiness with UC Functions**

---

## 🎯 Key Features

✅ **Production-Ready Whisper Transcription**
- PyTorch Whisper v3 Large deployed as Model Serving endpoint
- Scalable batch transcription via `ai_query()` function
- No local model loading - fully serverless

✅ **Lakeflow Spark Declarative Pipelines (SDP)**
- Latest Databricks data pipeline framework
- Auto Loader for incremental processing
- Medallion architecture: Bronze → Silver → Gold

✅ **Comprehensive AI Analysis**
- Sentiment analysis and call summarization
- Dynamic classification from lookup tables
- Named entity recognition and PII masking
- Compliance scoring with structured outputs
- Follow-up email generation with JSON schemas

✅ **Agent Integration Ready**
- 8 Unity Catalog Functions for data access
- Designed for Agent Bricks Knowledge Assistant
- Mock agent endpoints for testing
- Multi-agent workflow support

✅ **Customer-Ready Packaging**
- Clear documentation and setup guides
- Modular notebook structure
- Dashboard templates and workflow orchestration
- Sample data generators for demos

---

## 🗂 Project Structure

```
2025-06 automated-claims-processing/
├── config/
│   ├── config.py                          # Unified configuration (widgets, endpoints, helpers)
│   └── pipeline_config.yaml               # Lakeflow workflow configuration
├── setup/
│   ├── 00-setup.py                        # Initialize catalog/schema/volumes & lookup tables
│   ├── 01-deploy-whisper-endpoint.py      # Deploy PyTorch Whisper endpoint
│   └── sample_data_generator.py           # Generate synthetic demo data
├── pipeline/
│   ├── audio_processing_utils.py          # Audio metadata extraction utilities
│   └── 02-sdp-bronze-silver-gold.py       # Lakeflow SDP pipeline (Bronze → Silver → Gold)
├── tools/
│   └── 03-create-uc-tools.py              # Create 8 UC Functions for agent integration
├── agents_mock/
│   └── 04-mock-agent-endpoints.py         # Mock agent endpoints for testing
├── notebooks/
│   └── 05-prepare-dashboard-data.py       # Prepare aggregated data for dashboards
├── README.md                              # This file
├── IMPLEMENTATION_GUIDE.md                # Step-by-step implementation guide
└── call-center-analytics-workflow.yml     # Lakeflow workflow orchestration
```

---

## 🏗 Architecture

### Data Pipeline: Medallion Architecture with Lakeflow SDP

```
┌─────────────────────────────────────────────────────────────────┐
│                      🥉 BRONZE LAYER                             │
│  Auto Loader (cloudFiles) → Incremental Audio File Ingestion    │
│  - Detects new .wav/.mp3/.flac files                            │
│  - Binary file format ingestion                                 │
│  - Checkpoint-based exactly-once processing                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      🥈 SILVER LAYER                             │
│  Audio Transcription + Metadata Extraction                      │
│  - Parse filename → call_id, agent_id, datetime                 │
│  - Transcribe via Whisper endpoint (ai_query)                   │
│  - Extract duration and metadata                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      🥇 GOLD LAYER                              │ 
│  Comprehensive AI Enrichment with Batch AI Functions            │
│  ✓ Sentiment Analysis          ✓ Call Summarization             │
│  ✓ Call Reason Classification  ✓ Named Entity Recognition       │
│  ✓ PII Masking                 ✓ Compliance Scoring             │
│  ✓ Follow-up Email Generation                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Unity Catalog Functions (UC Tools)             │
│  Data Access Layer for Agent Integration                        │
│  - get_customer_policy_profile_by_phone_number()                │
│  - get_customer_sentiment_by_phone_number()                     │
│  - get_call_summary_by_phone_number()                           │
│  - get_compliance_score_by_phone_number()                       │
│  - ... and 4 more functions                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              📊 Dashboards & 🤖 Agent Bricks Integration         │
│  - Real-time analytics dashboards                               │
│  - Multi-agent workflows with LangGraph                         │
│  - Customer service automation                                  │
└─────────────────────────────────────────────────────────────────┘
```

### AI Analysis Pipeline

```
Audio File → Whisper Transcription → AI Enrichment → Insights
              (Model Serving)        (AI Functions)    (Gold Table)
```

**Endpoints Used:**
- **Whisper**: `whisper-v3-large-pytorch` (Model Serving endpoint)
- **LLM Reasoning**: `databricks-claude-3-7-sonnet` (compliance, email generation)
- **LLM Fast**: `databricks-meta-llama-3-3-70b-instruct` (classification, sentiment)

---

## 🚀 Quick Start

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- Model Serving permissions (for Whisper endpoint deployment)
- Access to Foundation Model endpoints (Claude, Llama)
- GPU quota for Whisper endpoint (GPU_MEDIUM or GPU_LARGE)

### Installation Steps

1. **Clone the repository** (or import notebooks into Databricks workspace)

2. **Configure the solution**
   ```python
   # Edit config/config.py to set:
   CATALOG = "call_center_analytics"
   SCHEMA = "main"
   VOLUME = "call_center_data"
   ```

3. **Run setup notebooks in sequence:**

   ```bash
   # Step 1: Initialize catalog, schema, volumes, lookup tables
   setup/00-setup.py

   # Step 2: Deploy Whisper endpoint (~15 minutes)
   setup/01-deploy-whisper-endpoint.py

   # Step 3: (Optional) Generate demo data
   setup/sample_data_generator.py
   ```

4. **Run the Lakeflow SDP pipeline:**

   ```bash
   # Execute Bronze → Silver → Gold pipeline
   pipeline/02-sdp-bronze-silver-gold.py
   ```

5. **Create UC Functions for agent integration:**

   ```bash
   tools/03-create-uc-tools.py
   ```

6. **Prepare dashboard data:**

   ```bash
   notebooks/05-prepare-dashboard-data.py
   ```

7. **Query the Gold table:**

   ```sql
   SELECT
       call_id,
       agent_id,
       call_datetime,
       sentiment,
       summary,
       classification,
       compliance_analysis.score as compliance_score
   FROM call_center_analytics.main.call_analysis_gold
   LIMIT 10;
   ```

For detailed implementation steps, see [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md).

---

## 📊 Data Schema

### Bronze Table: `raw_audio_files`

| Column | Type | Description |
|--------|------|-------------|
| `path` | STRING | Full path to audio file |
| `content` | BINARY | Audio file binary content |
| `length` | LONG | File size in bytes |
| `modificationTime` | TIMESTAMP | Last modified timestamp |

### Silver Table: `transcriptions_silver`

| Column | Type | Description |
|--------|------|-------------|
| `file_name` | STRING | Original filename |
| `call_id` | STRING | Unique call identifier |
| `agent_id` | STRING | Agent identifier |
| `call_datetime` | TIMESTAMP | Call date and time |
| `transcription` | STRING | Full call transcript |
| `duration_seconds` | DOUBLE | Call duration |
| `path` | STRING | Original file path |

### Gold Table: `call_analysis_gold`

| Column | Type | Description |
|--------|------|-------------|
| `call_id` | STRING | Unique call identifier |
| `agent_id` | STRING | Agent identifier |
| `call_datetime` | TIMESTAMP | Call date and time |
| `transcription` | STRING | Full call transcript |
| `duration_seconds` | DOUBLE | Call duration |
| `sentiment` | STRING | AI-detected sentiment |
| `summary` | STRING | AI-generated summary |
| `classification` | STRING | Call reason category |
| `entities` | STRUCT | Named entities (person, policy, date, phone, email) |
| `masked_transcript` | STRING | PII-masked transcript |
| `compliance_analysis` | STRUCT | Compliance score, violations, recommendations |
| `follow_up_email` | STRUCT | AI-generated follow-up email (subject, body, priority) |
| `customer_name` | STRING | Extracted customer name |
| `policy_number_extracted` | STRING | Extracted policy number |

---

## 🔧 Configuration

### Environment Configuration

The solution supports multiple environments (dev, staging, prod):

```python
# In config/config.py
dbutils.widgets.dropdown("ENVIRONMENT", "dev", ["dev", "prod", "demo"])
```

### Endpoint Configuration

Configure AI endpoints in `config/config.py`:

```python
# Whisper transcription endpoint
WHISPER_ENDPOINT_NAME = "whisper-v3-large-pytorch"

# Foundation Model endpoints for AI Functions
LLM_ENDPOINT_REASONING = "databricks-claude-3-7-sonnet"  # Complex reasoning
LLM_ENDPOINT_FAST = "databricks-meta-llama-3-3-70b-instruct"  # Fast operations
```

### Lookup Tables

Two lookup tables drive dynamic classification and compliance evaluation:

1. **`call_reasons`**: Maps call reasons to next steps and categories
2. **`compliance_guidelines`**: Defines compliance rules and severity levels

Both tables can be customized in `setup/00-setup.py`.

---

## 🤖 Agent Integration with Agent Bricks

This solution is designed for integration with **Agent Bricks Knowledge Assistant**, an external multi-agent system built with LangGraph.

### UC Functions for Agents

8 Unity Catalog Functions provide a secure, governed data access layer:

1. `get_customer_policy_profile_by_phone_number(phone)`
2. `get_customer_sentiment_by_phone_number(phone)`
3. `get_customer_transcript_by_phone_number(phone)`
4. `get_call_summary_by_phone_number(phone)`
5. `get_compliance_score_by_phone_number(phone)`
6. `get_follow_up_email_by_phone_number(phone)`
7. `get_call_history_by_phone_number(phone, limit_count)`
8. `search_calls_by_classification(call_reason, limit_count)`

### Agent Architecture

```
User Query → Supervisor Agent → Specialized Agents → UC Functions → Gold Table
                                ↓
                    - Customer Service Agent
                    - Policy Q&A Agent (with RAG)
                    - Compliance Agent
```

### Mock Agents for Testing

Mock agent endpoints are provided in `agents_mock/04-mock-agent-endpoints.py` for testing UC Functions before Agent Bricks deployment.

---

## 📈 Dashboard & Analytics

The solution includes pre-aggregated dashboard tables:

- **`dashboard_metrics`**: Real-time KPIs (call volume, sentiment, compliance)
- **`dashboard_trends`**: Time-series trends (hourly/daily)
- **`dashboard_agent_performance`**: Agent-level performance metrics
- **`dashboard_call_reasons`**: Call reason breakdown and analysis
- **`dashboard_compliance_issues`**: Compliance score distribution

### Sample Dashboard Queries

**Call Volume Trend:**
```sql
SELECT call_date, call_hour, call_count, avg_compliance
FROM dashboard_trends
ORDER BY call_date DESC, call_hour DESC
LIMIT 24
```

**Top Performing Agents:**
```sql
SELECT agent_id, total_calls, positive_percentage, avg_compliance_score
FROM dashboard_agent_performance
WHERE total_calls >= 5
ORDER BY avg_compliance_score DESC
LIMIT 10
```

---

## 🔄 Workflow Orchestration

The solution includes a Lakeflow workflow configuration (`config/pipeline_config.yaml`) that orchestrates:

1. Setup and initialization
2. Whisper endpoint deployment
3. SDP pipeline execution (Bronze → Silver → Gold)
4. UC Functions creation
5. Dashboard data preparation

**Triggers:**
- Manual execution
- File arrival (new audio files uploaded)
- Scheduled (e.g., daily at 2 AM)

---

## 🧪 Demo Data Generation

Generate synthetic call center data for testing:

```bash
# Generate 50 synthetic calls with realistic transcripts
setup/sample_data_generator.py
```

Includes:
- 5 fraud cases
- 3 financial hardship cases
- Various call reasons
- Realistic sentiment distribution
- Placeholder audio files

---

## 🖥 Recommended Cluster Configuration

### For Setup and Pipeline Execution
- **Databricks Runtime:** 14.3 LTS or later
- **Node Type:** i3.xlarge (4 cores, 30.5 GB RAM)
- **Workers:** 1-4 (autoscaling)
- **Photon:** Enabled

### For Whisper Endpoint Deployment
- **Workload Type:** GPU_MEDIUM (AWS) or GPU_LARGE (Azure)
- **Workload Size:** Small
- **Scale to Zero:** Enabled

---

## 📦 Dependencies

The solution automatically installs required dependencies:

- **mutagen** (>=1.47.0): Audio metadata extraction
- **faker** (>=20.0.0): Synthetic data generation

All AI functionality uses built-in Databricks AI Functions and Foundation Model endpoints—no additional ML libraries required.

---

## 🔐 Security & Governance

✅ **Unity Catalog Integration**
- All tables and functions registered in Unity Catalog
- Fine-grained access control on data and functions
- Audit logging for compliance

✅ **PII Protection**
- Automated PII masking with `ai_mask()`
- Sensitive fields masked in summaries and outputs

✅ **Endpoint Security**
- Model Serving endpoints with authentication
- UC Functions enforce row-level security
- Agent access controlled via Unity Catalog permissions

---

## 🛠 Troubleshooting

### Whisper Endpoint Deployment Issues
**Problem:** Endpoint deployment times out or fails
**Solution:**
- Check GPU quota in workspace
- Use `GPU_MEDIUM` for AWS, `GPU_LARGE` for Azure
- Wait up to 30 minutes for initial deployment

### Audio File Processing Issues
**Problem:** Files not processed or transcription empty
**Solution:**
- Verify audio file format (WAV, MP3, FLAC supported)
- Check file naming pattern: `{call_id}_{agent_id}_{datetime}.ext`
- Ensure Whisper endpoint is in "Ready" state

### AI Function Errors
**Problem:** `ai_query()` or `ai_classify()` fails
**Solution:**
- Verify Foundation Model endpoints are accessible
- Check endpoint names in `config/config.py`
- Ensure workspace has access to Foundation Models

---

## 📚 Additional Resources

- [Databricks AI Functions Documentation](https://docs.databricks.com/en/large-language-models/ai-functions.html)
- [Lakeflow Pipelines Guide](https://docs.databricks.com/en/delta-live-tables/index.html)
- [Unity Catalog Functions](https://docs.databricks.com/en/sql/language-manual/sql-ref-functions-udf.html)
- [Agent Framework](https://docs.databricks.com/en/generative-ai/agent-framework/index.html)

---

## ✅ Success Criteria

After successful deployment, you should have:

- ✅ Whisper PyTorch endpoint deployed and ready
- ✅ Lakeflow SDP pipeline processing audio files end-to-end
- ✅ Gold table with comprehensive AI enrichments
- ✅ 8 UC Functions ready for agent integration
- ✅ Dashboard tables with aggregated metrics
- ✅ Mock agent endpoints for testing

---

## 🎓 Use Cases

This solution accelerator is ideal for:

- **Call Center Operations**: Automated transcription and analysis
- **Quality Assurance**: Compliance monitoring and agent performance
- **Customer Experience**: Sentiment analysis and follow-up automation
- **Fraud Detection**: Identify suspicious calls and patterns
- **Agent Training**: Identify coaching opportunities
- **Regulatory Compliance**: Audit trails and compliance reporting

---

## 📄 License

This solution accelerator is provided as-is for demonstration and educational purposes.

**Open Source Dependencies:**
- **mutagen**: LGPL-2.1 (audio metadata extraction)
- **faker**: MIT License (synthetic data generation)

---

## 🚀 Ready to Get Started?

1. Review the [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) for step-by-step instructions
2. Run `setup/00-setup.py` to initialize your environment
3. Deploy the Whisper endpoint with `setup/01-deploy-whisper-endpoint.py`
4. Execute the full pipeline with `pipeline/02-sdp-bronze-silver-gold.py`
5. Create UC Functions with `tools/03-create-uc-tools.py`
6. Build dashboards using the prepared data tables

For questions or support, contact your Databricks account team or visit the [Databricks Community](https://community.databricks.com/).

---

**Built with ❤️ on the Databricks Intelligence Platform**
