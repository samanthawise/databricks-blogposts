# 🧠 AI-Powered Call Center Analytics – Solution Accelerator

A comprehensive Databricks solution accelerator that transforms call center data into actionable insights using **Synthetic Data Generation**, **AI Functions**, **Unity Catalog Functions**, and **AI/BI Dashboards**.

This solution demonstrates end-to-end call center analytics with:
- **Production-ready synthetic data generation** with realistic call transcripts
- **Comprehensive AI enrichment** using Databricks AI Functions
- **Agent-ready data access layer** with Unity Catalog Functions
- **Interactive AI/BI dashboards** for real-time analytics

---

## 🎯 Key Features

✅ **Realistic Synthetic Data Generation**
- 50 synthetic call scenarios with natural conversation flow
- Includes customer metadata (phone, email, DOB, policy numbers)
- Fraud and financial hardship scenarios
- Ready for demo and testing without real customer data

✅ **Comprehensive AI Analysis**
- Sentiment analysis and call summarization
- Dynamic classification from lookup tables
- Named entity recognition (ARRAY types for phone/email)
- PII masking and compliance scoring
- Follow-up email generation with JSON schemas

✅ **Agent Integration Ready**
- 8 Unity Catalog Functions for data access
- Designed for Agent Bricks Knowledge Assistant integration
- Phone and email lookups using ARRAY types
- Table-valued functions with flexible LIMIT

✅ **AI/BI Dashboard**
- Multi-page interactive dashboard
- Pre-aggregated metrics for fast queries
- Call volume trends, sentiment analysis, agent performance
- Compliance scoring and call reason breakdown

---

## 🗂 Project Structure

```
2025-06 automated-claims-processing/
├── config/
│   └── config.py                          # Unified configuration (widgets, endpoints, helpers)
├── setup/
│   ├── 00-setup.py                        # Initialize catalog/schema/volumes & lookup tables
│   ├── 01-deploy-whisper-endpoint.py      # (Optional) Deploy PyTorch Whisper endpoint
│   └── sample_data_generator.py           # Generate synthetic demo data with realistic transcripts
├── pipeline/
│   ├── audio_processing_utils.py          # Audio metadata extraction utilities
│   └── 02-sdp-bronze-silver-gold.py       # Gold layer AI enrichment pipeline
├── tools/
│   └── 03-create-uc-tools.py              # Create 8 UC Functions for agent integration
├── notebooks/
│   └── 05-prepare-dashboard-data.py       # Prepare aggregated data for dashboards
├── agents_mock/
│   └── 04-mock-agent-endpoints.py         # Mock agent endpoints for testing
├── raw_recordings/                         # (Optional) Audio files for transcription
├── README.md                              # This file
├── IMPLEMENTATION_GUIDE.md                # Step-by-step implementation guide
├── LICENSE.txt                            # License file
└── call-center-analytics-workflow.yml     # Workflow orchestration configuration
```

---

## 🏗 Architecture

### Current Implementation: Synthetic Data + AI Enrichment

```
┌─────────────────────────────────────────────────────────────────┐
│                  DATA GENERATION                                │
│  Synthetic Call Data Generator (Faker + PySpark)                │
│  - 50 realistic call transcripts with natural conversation      │
│  - Customer metadata (name, phone, email, DOB, policy)          │
│  - Explicit dates and entity mentions for accurate extraction   │
│  Output: synthetic_call_data, transcriptions_silver             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  GOLD LAYER AI ENRICHMENT                       │
│  Comprehensive AI Analysis with Batch AI Functions              │
│  ✓ Sentiment Analysis          ✓ Call Summarization             │
│  ✓ Call Reason Classification  ✓ Named Entity Recognition       │
│  ✓ PII Masking                 ✓ Compliance Scoring (JSON)      │
│  ✓ Follow-up Email Generation (JSON Schema)                     │
│  Output: call_analysis_gold (with phone_numbers as ARRAY)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Unity Catalog Functions (UC Tools)             │
│  Data Access Layer for Agent Integration                        │
│  - get_customer_policy_profile_by_phone_number(phone)           │
│  - get_customer_sentiment_by_phone_number(phone)                │
│  - get_call_summary_by_phone_number(phone)                      │
│  - get_compliance_score_by_phone_number(phone)                  │
│  - get_call_history_by_phone_number(phone) + LIMIT              │
│  - ... and 3 more functions                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Dashboard Aggregation & Visualization          │
│  - Pre-aggregated metrics (5 tables)                            │
│  - AI/BI Dashboard (4 pages: Overview, Trends, Agents, Reasons) │
│  - Real-time KPIs and analytics                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Optional: Audio Transcription with Whisper

The solution can be extended to process real audio files:

```
Audio Files → Whisper Transcription → AI Enrichment → Insights
              (Model Serving)        (AI Functions)    (Gold Table)
```

**To enable audio processing:**
1. Uncomment Whisper endpoint deployment in workflow
2. Upload audio files to `raw_recordings` volume
3. Enable Bronze/Silver layers in pipeline

**Endpoints Used:**
- **Whisper** (optional): `va_whisper_large_v3` (Model Serving endpoint)
- **LLM Reasoning**: `databricks-claude-sonnet-4-5` (compliance, email generation)
- **LLM Fast**: `databricks-gpt-5-nano` (classification, sentiment)

---

## 🚀 Quick Start

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- Access to Foundation Model endpoints (Claude Sonnet 4.5)
- (Optional) Model Serving permissions for Whisper endpoint
- (Optional) GPU quota if processing real audio files

### Installation Steps

1. **Clone the repository** (or import notebooks into Databricks workspace)

2. **Configure the solution**
   ```python
   # Edit config/config.py widgets (or accept defaults):
   CATALOG = "call_center_analytics"
   SCHEMA = "main"
   VOLUME = "call_center_data"
   ```

3. **Run setup notebooks in sequence:**

   ```bash
   # Step 1: Initialize catalog, schema, volumes, lookup tables
   setup/00-setup.py

   # Step 2: Generate synthetic call data (50 realistic transcripts)
   setup/sample_data_generator.py

   # Step 3: (Optional) Deploy Whisper endpoint for real audio processing
   # setup/01-deploy-whisper-endpoint.py
   ```

4. **Run the Gold Layer AI Enrichment Pipeline:**

   ```bash
   # Execute AI enrichment on transcriptions_silver
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
       compliance_analysis.score as compliance_score,
       phone_numbers,  -- Now an ARRAY type
       email_addresses  -- Now an ARRAY type
   FROM call_center_analytics.main.call_analysis_gold
   LIMIT 10;
   ```

For detailed implementation steps, see [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md).

---

## 📊 Data Schema

### Silver Table: `transcriptions_silver`

| Column | Type | Description |
|--------|------|-------------|
| `call_id` | STRING | Unique call identifier |
| `agent_id` | STRING | Agent identifier |
| `call_datetime` | TIMESTAMP | Call date and time |
| `customer_name` | STRING | Customer name |
| `phone_number` | STRING | Customer phone number |
| `email` | STRING | Customer email address |
| `dob` | DATE | Customer date of birth |
| `policy_number` | STRING | Policy number |
| `duration_seconds` | DOUBLE | Call duration |
| `transcription` | STRING | Full call transcript |
| `filename` | STRING | Original filename |
| `category` | STRING | Call category (general, fraud, hardship) |
| `reason_for_call` | STRING | Reason for the call |

### Gold Table: `call_analysis_gold`

| Column | Type | Description |
|--------|------|-------------|
| `call_id` | STRING | Unique call identifier |
| `agent_id` | STRING | Agent identifier |
| `call_datetime` | TIMESTAMP | Call date and time |
| `customer_name` | STRING | Customer name |
| `phone_number` | STRING | Original phone number |
| `email` | STRING | Customer email |
| `dob` | DATE | Customer date of birth |
| `policy_number` | STRING | Policy number |
| `transcription` | STRING | Full call transcript |
| `duration_seconds` | DOUBLE | Call duration |
| `sentiment` | STRING | AI-detected sentiment |
| `summary` | STRING | AI-generated summary |
| `classification` | STRING | Call reason category |
| `entities` | STRUCT | Named entities (person, policy, date, phone, email) |
| `masked_transcript` | STRING | PII-masked transcript |
| `compliance_analysis` | STRUCT | Compliance score, violations, recommendations |
| `follow_up_email` | STRUCT | AI-generated email (subject, body, priority) |
| `phone_numbers` | ARRAY<STRING> | **Extracted phone numbers as ARRAY** |
| `email_addresses` | ARRAY<STRING> | **Extracted email addresses as ARRAY** |
| `dates_mentioned` | STRING | Extracted dates |
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
# Whisper transcription endpoint (optional)
WHISPER_ENDPOINT_NAME = "va_whisper_large_v3"

# Foundation Model endpoints for AI Functions
LLM_ENDPOINT_REASONING = "databricks-claude-sonnet-4-5"  # Complex reasoning
LLM_ENDPOINT_FAST = "databricks-gpt-5-nano"  # Fast operations
```

### Lookup Tables

Two lookup tables drive dynamic classification and compliance evaluation:

1. **`call_reasons`**: Maps call reasons to next steps and categories
2. **`compliance_guidelines`**: Defines compliance rules and severity levels

Both tables can be customized in `setup/00-setup.py`.

---

## 🤖 Agent Integration with Agent Bricks

This solution is designed for integration with **Agent Bricks Knowledge Assistant**, an external multi-agent system that handles all orchestration and agentic workflows.

### UC Functions for Agents

8 Unity Catalog Functions provide a secure, governed data access layer:

1. `get_customer_policy_profile_by_phone_number(phone)` - Returns customer profile
2. `get_customer_sentiment_by_phone_number(phone)` - Returns sentiment
3. `get_customer_transcript_by_phone_number(phone)` - Returns full transcript
4. `get_call_summary_by_phone_number(phone)` - Returns AI summary
5. `get_compliance_score_by_phone_number(phone)` - Returns compliance analysis
6. `get_follow_up_email_by_phone_number(phone)` - Returns generated email JSON
7. `get_call_history_by_phone_number(phone)` - Returns call history (apply LIMIT when querying)
8. `search_calls_by_classification(call_reason)` - Searches by call reason (apply LIMIT when querying)

**Note:** Table-valued functions (7 & 8) do not take limit parameters. Apply LIMIT when querying:
```sql
SELECT * FROM get_call_history_by_phone_number('(555)-123-4567') LIMIT 5;
```

### Key Implementation Details

- **ARRAY Types**: `phone_numbers` and `email_addresses` are stored as ARRAY<STRING> to support `ARRAY_CONTAINS` queries
- **JSON Schema Responses**: Compliance scoring and email generation use structured JSON output
- **No Speaker Labels**: Transcripts use natural conversation flow without "Agent:" or "Customer:" labels

---

## 📈 Dashboard & Analytics

The solution includes an **AI/BI Dashboard** with 4 pages:

1. **Overview**: KPIs, sentiment distribution, compliance breakdown, top call reasons
2. **Trends**: Call volume trends, compliance score trends, duration trends
3. **Agent Performance**: Compliance by agent, call volume, performance table
4. **Call Reasons Analysis**: Call reason distribution, duration analysis, details table

### Dashboard Tables

Pre-aggregated tables for fast queries:

- **`dashboard_metrics`**: Real-time KPIs (1 row with summary statistics)
- **`dashboard_trends`**: Time-series trends (by date and hour)
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

The solution includes a workflow configuration (`call-center-analytics-workflow.yml`) that orchestrates:

1. Setup and initialization (catalog, schema, volumes, lookup tables)
2. Synthetic data generation (50 realistic call transcripts)
3. (Optional) Whisper endpoint deployment
4. Gold layer AI enrichment pipeline
5. UC Functions creation (8 functions)
6. Dashboard data preparation (5 aggregation tables)

**Triggers:**
- Manual execution
- Scheduled (e.g., daily at 2 AM for periodic data refresh)
- (Optional) File arrival trigger for real audio files

---

## 🧪 Synthetic Data Generation

Generate 50 realistic call center scenarios:

```bash
setup/sample_data_generator.py
```

Includes:
- 5 fraud attempt cases
- 3 financial hardship cases
- 14 different call reasons (claim status, billing, coverage, etc.)
- Natural conversation format without speaker labels
- Customer metadata (phone, email, DOB) embedded in transcripts
- Explicit dates for accurate entity extraction
- Realistic sentiment distribution (positive, neutral, negative)

---

## 🖥 Recommended Cluster Configuration

### For Setup and Pipeline Execution
- **Databricks Runtime:** 14.3 LTS or later
- **Node Type:** i3.xlarge (4 cores, 30.5 GB RAM)
- **Workers:** 1-4 (autoscaling)
- **Photon:** Enabled

### For Whisper Endpoint Deployment (Optional)
- **Workload Type:** GPU_MEDIUM (AWS) or GPU_LARGE (Azure)
- **Workload Size:** Small
- **Scale to Zero:** Enabled

---

## 📦 Dependencies

The solution automatically installs required dependencies:

- **mutagen** (>=1.47.0): Audio metadata extraction (if processing audio)
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
- ARRAY types prevent accidental data leakage

✅ **Endpoint Security**
- Model Serving endpoints with authentication
- UC Functions enforce row-level security
- Agent access controlled via Unity Catalog permissions

---

## 🛠 Troubleshooting

### UC Functions ARRAY_CONTAINS Errors
**Problem:** UC Functions fail with "ARRAY_CONTAINS expects ARRAY type" error
**Solution:**
- Ensure Gold pipeline ran with latest code
- Verify `phone_numbers` and `email_addresses` are ARRAY types
- Re-run pipeline if needed: `pipeline/02-sdp-bronze-silver-gold.py`

### AI Function Errors
**Problem:** `ai_query()` or `ai_classify()` fails
**Solution:**
- Verify Foundation Model endpoints are accessible
- Check endpoint names in `config/config.py`
- Ensure workspace has access to Claude Sonnet 4.5

### Dashboard Shows No Data
**Problem:** Dashboard widgets empty or no data
**Solution:**
- Verify Gold table has data: `SELECT COUNT(*) FROM call_analysis_gold`
- Re-run dashboard prep: `notebooks/05-prepare-dashboard-data.py`
- Check that aggregation tables were created successfully

---

## 📚 Additional Resources

- [Databricks AI Functions Documentation](https://docs.databricks.com/en/large-language-models/ai-functions.html)
- [Unity Catalog Functions](https://docs.databricks.com/en/sql/language-manual/sql-ref-functions-udf.html)
- [AI/BI Dashboards](https://docs.databricks.com/en/dashboards/index.html)
- [Agent Framework](https://docs.databricks.com/en/generative-ai/agent-framework/index.html)

---

## ✅ Success Criteria

After successful deployment, you should have:

- ✅ Synthetic call data with 50 realistic transcripts
- ✅ Gold table with comprehensive AI enrichments
- ✅ phone_numbers and email_addresses as ARRAY<STRING> types
- ✅ 8 UC Functions ready for agent integration
- ✅ 5 dashboard aggregation tables with metrics
- ✅ AI/BI Dashboard with 4 interactive pages

---

## 🎓 Use Cases

This solution accelerator is ideal for:

- **Call Center Operations**: Automated transcription and analysis
- **Quality Assurance**: Compliance monitoring and agent performance
- **Customer Experience**: Sentiment analysis and follow-up automation
- **Fraud Detection**: Identify suspicious calls and patterns
- **Agent Training**: Identify coaching opportunities
- **Regulatory Compliance**: Audit trails and compliance reporting
- **Demo and Testing**: Synthetic data for proof-of-concepts

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
3. Generate synthetic data with `setup/sample_data_generator.py`
4. Execute the AI enrichment pipeline with `pipeline/02-sdp-bronze-silver-gold.py`
5. Create UC Functions with `tools/03-create-uc-tools.py`
6. Prepare and view the AI/BI Dashboard

For questions or support, contact your Databricks account team or visit the [Databricks Community](https://community.databricks.com/).

---

**Built with ❤️ on the Databricks Intelligence Platform**
