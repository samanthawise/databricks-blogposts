# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Sample Call Center Data
# MAGIC
# MAGIC This notebook generates synthetic call center data for testing and demonstration:
# MAGIC - 50 synthetic call scenarios with customer metadata
# MAGIC - Realistic call transcripts (natural conversation format without speaker labels)
# MAGIC - Saves data to Unity Catalog tables
# MAGIC
# MAGIC **Use Case:** Demo and testing the claims processing pipeline without real customer data

# COMMAND ----------

# DBTITLE 1,Install Dependencies (if needed)
# MAGIC %pip install -U --quiet faker
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Configuration
# MAGIC %run ../config/config

# COMMAND ----------

# DBTITLE 1,Import Libraries
import random
import uuid
from datetime import datetime, timedelta
from pyspark.sql import Row
from pyspark.sql import functions as F
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

def generate_transcript(customer_name, policy_number, reason_for_call, sentiment, phone_number=None, email=None, dob=None):
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

    # Verification - include phone number and occasionally DOB
    verification_parts = [f"Of course, I'd be happy to help with that. For security purposes, can I confirm your policy number?"]
    verification_response_parts = [f"Yes, it's {policy_number}."]

    # Add phone number to verification
    if phone_number:
        verification_parts.append(f"And can I get a callback number in case we get disconnected?")
        verification_response_parts.append(f"Sure, it's {phone_number}.")

    # Occasionally verify DOB for high-value/fraud cases
    if dob and random.random() < 0.3:  # 30% of calls verify DOB
        verification_parts.append(f"For additional security, can I also confirm your date of birth?")
        verification_response_parts.append(f"It's {dob.strftime('%B %d, %Y')}.")

    verification = " ".join(verification_parts)
    verification_response = " ".join(verification_response_parts)

    # Generate some dates for discussion
    claim_submission_date = datetime.now() - timedelta(days=random.randint(7, 21))
    expected_decision_date = datetime.now() + timedelta(days=random.randint(3, 7))
    next_payment_date = datetime.now() + timedelta(days=random.randint(5, 30))

    # Issue discussion (varies by reason) - include explicit dates
    if "claim" in reason_for_call.lower():
        discussion = [
            "Thank you for confirming. Let me pull up your account... I can see your claim here. What specific information did you need?",
            f"I wanted to check on the status. I submitted it on {claim_submission_date.strftime('%B %d, %Y')}.",
            f"I understand your concern. Let me check the current status... Your claim is currently under review by our medical assessment team. You should expect a decision by {expected_decision_date.strftime('%B %d, %Y')}.",
        ]
    elif "billing" in reason_for_call.lower():
        discussion = [
            "Let me review your account details... I can see your billing history here. What specific question did you have?",
            "My premium payment seems higher than usual this month. Can you explain why?",
            f"I see there was an adjustment to your premium due to a policy update effective {(datetime.now() - timedelta(days=30)).strftime('%B %d, %Y')}. Your next payment of $150 is due on {next_payment_date.strftime('%B %d, %Y')}.",
        ]
    elif "coverage" in reason_for_call.lower():
        discussion = [
            "I'd be happy to explain your coverage details. What specific aspect would you like to know about?",
            "I'm wondering if my policy covers physiotherapy sessions?",
            f"Yes, your current plan includes up to 10 physiotherapy sessions per year. Your coverage period renews on {(datetime.now() + timedelta(days=90)).strftime('%B %d, %Y')}.",
        ]
    else:
        discussion = [
            "Let me assist you with that. Can you provide more details about your inquiry?",
            f"I need help with {reason_for_call.lower()}.",
            "I understand. Let me see what I can do to help you with this...",
        ]

    # Resolution and closing (varies by sentiment) - include email in closing
    if sentiment in ["Frustrated", "Angry"]:
        resolution = "I apologize for the inconvenience this has caused. I want to make sure we resolve this to your satisfaction. I'm going to escalate this to my supervisor, and you'll receive a call back within 24 hours. Is there anything else I can help clarify right now?"
        customer_end = "No, I just want this resolved quickly."
        if email:
            closing = f"I completely understand. We'll prioritize this and be in touch soon. I'll also send a confirmation email to {email} with the details of our conversation. Thank you for your patience."
        else:
            closing = "I completely understand. We'll prioritize this and be in touch soon. Thank you for your patience."
    elif sentiment == "Happy":
        resolution = "Is there anything else I can help you with today?"
        customer_end = "No, that's everything. Thanks so much for your help!"
        if email:
            closing = f"You're very welcome! I'll send you a summary email to {email} for your records. If you need anything else, don't hesitate to call us. Have a great day!"
        else:
            closing = "You're very welcome! If you need anything else, don't hesitate to call us. Have a great day!"
    else:  # Neutral, Confused
        resolution = "Just to summarize what we've discussed... Does that all make sense? Do you have any other questions?"
        customer_end = "Yes, that's clear. Thank you for explaining."
        if email:
            closing = f"You're welcome! I'll send you a confirmation email to {email} with all the details we discussed. If anything else comes up, feel free to reach out. Take care!"
        else:
            closing = "You're welcome! If anything else comes up, feel free to reach out. Take care!"

    # Assemble transcript (no speaker labels, natural flowing conversation)
    transcript_parts = [
        greeting,
        intro,
        verification,
        verification_response,
    ]

    transcript_parts.extend(discussion)

    transcript_parts.extend([
        resolution,
        customer_end,
        closing,
        "Goodbye.",
        "Goodbye!"
    ])

    return " ".join(transcript_parts)

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
    email = fake.email()  # Generate email address
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
    call_datetime = random_datetime_past_30_days()
    call_id = generate_call_id()
    agent_id = generate_agent_id()
    duration = random_call_duration()

    # Generate transcript with all entity information
    transcript = generate_transcript(
        customer_name,
        policy_number,
        reason_data['reason_for_call'],
        sentiment,
        phone_number=phone_number,
        email=email,
        dob=dob
    )

    # Create filename pattern: {call_id}_{agent_id}_{datetime}.wav
    filename = f"{call_id}_{agent_id}_{call_datetime.strftime('%Y-%m-%d_%H-%M-%S')}.wav"

    call_data.append(Row(
        call_id=call_id,
        agent_id=agent_id,
        call_datetime=call_datetime,
        customer_name=customer_name,
        phone_number=phone_number,
        email=email,  # Add email field
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

# DBTITLE 1,Create Silver Layer Table

# Create a silver layer table from synthetic_call_data with standardized column names
print("Creating silver layer table from synthetic call data...")

silver_table_name = f"{CATALOG}.{SCHEMA}.transcriptions_silver"

# Read synthetic_call_data and rename 'transcript' to 'transcription'
silver_df = spark.table(f"{CATALOG}.{SCHEMA}.synthetic_call_data").select(
    "call_id",
    "agent_id",
    "call_datetime",
    "customer_name",
    "phone_number",
    "email",  # Include email field
    "dob",    # Include dob field
    "policy_number",
    "duration_seconds",
    F.col("transcript").alias("transcription"),  # Rename for pipeline consistency
    "filename",
    "category",
    "reason_for_call"
)

# Save as silver table
silver_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(silver_table_name)

print(f"✓ Created silver layer table: {silver_table_name}")
print(f"  - Renamed 'transcript' to 'transcription' column")
print(f"  - {silver_df.count()} records")

# COMMAND ----------

# DBTITLE 1,Sample Data Generation Summary

print("\n" + "=" * 80)
print("SAMPLE DATA GENERATION COMPLETE")
print("=" * 80)
print(f"\n✓ Generated {NUM_CALLS} synthetic call scenarios")
print(f"  - {NUM_FRAUD_CASES} fraud cases")
print(f"  - {NUM_HARDSHIP_CASES} financial hardship cases")
print(f"  - {NUM_CALLS - NUM_FRAUD_CASES - NUM_HARDSHIP_CASES} general inquiries")
print(f"\n✅ Tables Created:")
print(f"  1. {CATALOG}.{SCHEMA}.synthetic_call_data (raw synthetic data)")
print(f"  2. {CATALOG}.{SCHEMA}.transcriptions_silver (silver layer)")
print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. Run the Gold layer pipeline: pipeline/02-sdp-bronze-silver-gold.py")
print("2. The pipeline will read from transcriptions_silver table")
print("3. AI enrichments will be applied (sentiment, NER, compliance, etc.)")
print("=" * 80)

# COMMAND ----------

# DBTITLE 1,Display Sample Transcript
print("\nSample Generated Transcript:")
print("=" * 80)
sample_transcript = df_calls.select("transcript").first()['transcript']
print(sample_transcript)
print("=" * 80)
