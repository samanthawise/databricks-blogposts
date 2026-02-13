# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Sample Call Center Data
# MAGIC
# MAGIC This notebook generates synthetic call center data for testing and demonstration:
# MAGIC - 50 synthetic call scenarios with customer metadata
# MAGIC - Realistic call transcripts
# MAGIC - Sample audio file placeholders (for testing the pipeline)
# MAGIC - Saves data to Unity Catalog volumes and tables
# MAGIC
# MAGIC **Use Case:** Demo and testing the Lakeflow SDP pipeline without real customer data

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Install Dependencies (if needed)
# MAGIC %pip install -U --quiet faker
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
import random
import uuid
from datetime import datetime, timedelta
from pyspark.sql import Row
from faker import Faker

# Initialize Faker for realistic data generation
fake = Faker(['en_US', 'en_GB'])
Faker.seed(42)  # For reproducibility

# COMMAND ----------

# DBTITLE 1,Configuration
NUM_CALLS = 50  # Number of synthetic calls to generate
NUM_AGENTS = 5  # Number of call center agents
NUM_FRAUD_CASES = 5  # Number of fraud cases
NUM_HARDSHIP_CASES = 3  # Number of financial hardship cases

print(f"Generating {NUM_CALLS} synthetic call scenarios...")

# COMMAND ----------

# DBTITLE 1,Helper Functions

def random_datetime_past_30_days():
    """Generate random datetime within past 30 days"""
    return datetime.now() - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

def generate_call_id():
    """Generate unique call ID"""
    return str(uuid.uuid4())[:8].upper()

def generate_agent_id():
    """Generate agent ID"""
    return f"AGT{str(random.randint(1, NUM_AGENTS)).zfill(3)}"

def generate_policy_number():
    """Generate policy number"""
    return f"VG{random.randint(100000, 999999)}"

def random_call_duration():
    """Generate call duration between 1-10 minutes"""
    return random.randint(60, 600)  # 1-10 minutes in seconds

def random_phone_number():
    """Generate phone number"""
    return f"({random.randint(100, 999)})-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

# COMMAND ----------

# DBTITLE 1,Load Call Reasons from Lookup Table

# Read call reasons from the lookup table created in setup
df_call_reasons = spark.table(f"{CATALOG}.{SCHEMA}.{CALL_REASONS_TABLE}")
call_reasons_list = [row.asDict() for row in df_call_reasons.collect()]

# Separate by category
general_reasons = [r for r in call_reasons_list if r['category'] == 'general']
hardship_reasons = [r for r in call_reasons_list if r['category'] == 'financial_hardship']
fraud_reasons = [r for r in call_reasons_list if r['category'] == 'fraud']

print(f"Loaded {len(call_reasons_list)} call reasons from lookup table")

# COMMAND ----------

# DBTITLE 1,Generate Call Transcripts

def generate_transcript(customer_name, policy_number, reason_for_call, sentiment):
    """Generate realistic call transcript based on scenario"""

    agent = f"Agent {random.randint(100, 999)}"

    # Greeting based on time of day
    greeting_options = [
        f"Good morning, thank you for calling VitalGuard Insurance. My name is {agent}. How may I assist you today?",
        f"Good afternoon, this is {agent} from VitalGuard Insurance. How can I help you?",
        f"Thank you for calling VitalGuard Insurance, this is {agent}. What can I do for you today?"
    ]
    greeting = random.choice(greeting_options)

    # Customer introduction
    intro = f"Hi, my name is {customer_name}. I'm calling about {reason_for_call.lower()}."

    # Verification
    verification = f"Of course, I'd be happy to help with that. For security purposes, can I confirm your policy number?"
    verification_response = f"Yes, it's {policy_number}."

    # Issue discussion (varies by reason)
    if "claim" in reason_for_call.lower():
        discussion = [
            "Thank you for confirming. Let me pull up your account... I can see your claim here. What specific information did you need?",
            "I wanted to check on the status. It's been two weeks since I submitted it.",
            "I understand your concern. Let me check the current status... Your claim is currently under review by our medical assessment team. You should expect a decision within 3-5 business days.",
        ]
    elif "billing" in reason_for_call.lower():
        discussion = [
            "Let me review your account details... I can see your billing history here. What specific question did you have?",
            "My premium payment seems higher than usual this month. Can you explain why?",
            "I see there was an adjustment to your premium due to a policy update. Let me walk you through the changes...",
        ]
    elif "coverage" in reason_for_call.lower():
        discussion = [
            "I'd be happy to explain your coverage details. What specific aspect would you like to know about?",
            "I'm wondering if my policy covers physiotherapy sessions?",
            "Yes, your current plan includes up to 10 physiotherapy sessions per year, but they need to be prescribed by your GP.",
        ]
    else:
        discussion = [
            "Let me assist you with that. Can you provide more details about your inquiry?",
            f"I need help with {reason_for_call.lower()}.",
            "I understand. Let me see what I can do to help you with this...",
        ]

    # Resolution and closing (varies by sentiment)
    if sentiment in ["Frustrated", "Angry"]:
        resolution = "I apologize for the inconvenience this has caused. I want to make sure we resolve this to your satisfaction. I'm going to escalate this to my supervisor, and you'll receive a call back within 24 hours. Is there anything else I can help clarify right now?"
        customer_end = "No, I just want this resolved quickly."
        closing = "I completely understand. We'll prioritize this and be in touch soon. Thank you for your patience."
    elif sentiment == "Happy":
        resolution = "Is there anything else I can help you with today?"
        customer_end = "No, that's everything. Thanks so much for your help!"
        closing = "You're very welcome! If you need anything else, don't hesitate to call us. Have a great day!"
    else:  # Neutral, Confused
        resolution = "Just to summarize what we've discussed... Does that all make sense? Do you have any other questions?"
        customer_end = "Yes, that's clear. Thank you for explaining."
        closing = "You're welcome! If anything else comes up, feel free to reach out. Take care!"

    # Assemble transcript
    transcript_parts = [
        f"Agent: {greeting}",
        f"Customer: {intro}",
        f"Agent: {verification}",
        f"Customer: {verification_response}",
    ]

    for line in discussion:
        speaker = "Agent" if transcript_parts[-1].startswith("Customer") else "Customer"
        transcript_parts.append(f"{speaker}: {line}")

    transcript_parts.extend([
        f"Agent: {resolution}",
        f"Customer: {customer_end}",
        f"Agent: {closing}",
        "Customer: Goodbye.",
        "Agent: Goodbye!"
    ])

    return "\n\n".join(transcript_parts)

# COMMAND ----------

# DBTITLE 1,Generate Synthetic Call Data

sentiments = ["Happy", "Neutral", "Frustrated", "Angry", "Confused"]

call_data = []

# Determine which indices will be fraud and hardship
fraud_indices = set(random.sample(range(NUM_CALLS), min(NUM_FRAUD_CASES, NUM_CALLS)))
remaining_indices = list(set(range(NUM_CALLS)) - fraud_indices)
hardship_indices = set(random.sample(remaining_indices, min(NUM_HARDSHIP_CASES, len(remaining_indices))))

for i in range(NUM_CALLS):
    # Determine call reason and category
    if i in fraud_indices:
        reason_data = fraud_reasons[0]
        sentiment = random.choice(["Frustrated", "Angry", "Confused"])
    elif i in hardship_indices:
        reason_data = random.choice(hardship_reasons)
        sentiment = random.choice(["Neutral", "Frustrated", "Confused"])
    else:
        reason_data = random.choice(general_reasons)
        sentiment = random.choice(sentiments)

    # Generate customer data
    customer_name = fake.name()
    policy_number = generate_policy_number()
    phone_number = random_phone_number()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
    call_datetime = random_datetime_past_30_days()
    call_id = generate_call_id()
    agent_id = generate_agent_id()
    duration = random_call_duration()

    # Generate transcript
    transcript = generate_transcript(
        customer_name,
        policy_number,
        reason_data['reason_for_call'],
        sentiment
    )

    # Create filename pattern: {call_id}_{agent_id}_{datetime}.wav
    filename = f"{call_id}_{agent_id}_{call_datetime.strftime('%Y-%m-%d_%H-%M-%S')}.wav"

    call_data.append(Row(
        call_id=call_id,
        agent_id=agent_id,
        call_datetime=call_datetime,
        customer_name=customer_name,
        phone_number=phone_number,
        dob=dob,
        policy_number=policy_number,
        sentiment=sentiment,
        reason_for_call=reason_data['reason_for_call'],
        next_steps=reason_data['next_steps'],
        duration_seconds=duration,
        transcript=transcript,
        filename=filename,
        category=reason_data['category']
    ))

# Create DataFrame
df_calls = spark.createDataFrame(call_data)

print(f"✓ Generated {df_calls.count()} synthetic call records")
display(df_calls.select("call_id", "agent_id", "customer_name", "reason_for_call", "sentiment", "duration_seconds").limit(10))

# COMMAND ----------

# DBTITLE 1,Save Synthetic Transcripts to Table

# Save to table for reference
df_calls.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.synthetic_call_data"
)

print(f"✓ Saved synthetic call data to table: {CATALOG}.{SCHEMA}.synthetic_call_data")

# COMMAND ----------

# DBTITLE 1,Create Sample Audio File Placeholders

# Create placeholder audio files (empty files with correct names)
# In a real scenario, you would generate actual audio or use TTS

print(f"Creating {NUM_CALLS} placeholder audio files...")

for row in df_calls.select("filename", "transcript", "duration_seconds").collect():
    filename = row['filename']
    transcript = row['transcript']
    duration = row['duration_seconds']

    # Create a simple text file as placeholder
    # In production, this would be actual audio (WAV/MP3)
    file_path = f"{raw_audio_path}{filename}"

    # Write transcript as placeholder (for demo purposes)
    # Real implementation would write actual audio bytes
    with open(file_path.replace("/Volumes/", "/Volumes/"), "w") as f:
        f.write(f"# PLACEHOLDER AUDIO FILE\n")
        f.write(f"# Duration: {duration} seconds\n")
        f.write(f"# Filename: {filename}\n")
        f.write(f"#\n")
        f.write(f"# In production, this would be actual audio data.\n")
        f.write(f"# For demo purposes, this file contains the transcript:\n")
        f.write(f"#\n")
        f.write(transcript)

print(f"✓ Created {NUM_CALLS} placeholder audio files in: {raw_audio_path}")

# Note about placeholder files
print("\n⚠️  NOTE: These are placeholder text files, not actual audio.")
print("   In production, you would:")
print("   1. Record actual calls as WAV/MP3 files")
print("   2. Use Text-to-Speech to generate synthetic audio")
print("   3. Download sample audio files from a data source")

# COMMAND ----------

# DBTITLE 1,Sample Data Generation Summary

print("\n" + "=" * 80)
print("SAMPLE DATA GENERATION COMPLETE")
print("=" * 80)
print(f"\n✓ Generated {NUM_CALLS} synthetic call scenarios")
print(f"  - {NUM_FRAUD_CASES} fraud cases")
print(f"  - {NUM_HARDSHIP_CASES} financial hardship cases")
print(f"  - {NUM_CALLS - NUM_FRAUD_CASES - NUM_HARDSHIP_CASES} general inquiries")
print(f"\n✓ Created placeholder audio files in: {raw_audio_path}")
print(f"✓ Saved synthetic data to table: {CATALOG}.{SCHEMA}.synthetic_call_data")
print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. Run the Lakeflow SDP pipeline: pipeline/02-sdp-bronze-silver-gold.py")
print("2. The pipeline will:")
print("   - Ingest audio files from volume (Bronze layer)")
print("   - Transcribe using Whisper endpoint (Silver layer)")
print("   - Enrich with AI analysis (Gold layer)")
print("=" * 80)

# COMMAND ----------

# DBTITLE 1,Display Sample Transcript
print("\nSample Generated Transcript:")
print("=" * 80)
sample_transcript = df_calls.select("transcript").first()['transcript']
print(sample_transcript)
print("=" * 80)
