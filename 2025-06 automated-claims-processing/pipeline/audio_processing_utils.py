# Databricks notebook source
# MAGIC %md
# MAGIC # Audio Processing Utilities
# MAGIC
# MAGIC This module provides utility functions for audio file processing:
# MAGIC - Extract audio metadata (duration, format)
# MAGIC - Parse filename to extract call metadata (call_id, agent_id, datetime)
# MAGIC - Helper functions for audio format detection
# MAGIC
# MAGIC **Expected Filename Pattern:** `{call_id}_{agent_id}_{YYYY-MM-DD_HH-MM-SS}.{ext}`
# MAGIC Example: `ABC123_AGT001_2024-01-15_10-30-45.wav`

# COMMAND ----------

# DBTITLE 1,Import Libraries
# Note: Dependencies (mutagen) should be installed before running this notebook
# Install in the main pipeline notebook before importing config and this module
from pyspark.sql.functions import udf, col, split, regexp_extract, regexp_replace, to_timestamp, concat_ws
from pyspark.sql.types import FloatType, StringType, StructType, StructField
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen import File as MutagenFile
import os

# COMMAND ----------

# DBTITLE 1,Audio Duration Extraction

def get_audio_duration(file_path: str) -> float:
    """
    Extract audio duration in seconds using mutagen library.

    Args:
        file_path: Full path to the audio file

    Returns:
        Duration in seconds (float), or None if extraction fails
    """
    try:
        # Try to detect format automatically
        audio = MutagenFile(file_path)

        if audio is None:
            print(f"⚠️ Could not detect audio format for: {file_path}")
            return None

        # Get duration from info
        if hasattr(audio.info, 'length'):
            return float(audio.info.length)
        else:
            print(f"⚠️ No duration info available for: {file_path}")
            return None

    except Exception as e:
        print(f"⚠️ Error extracting duration from {file_path}: {e}")
        return None


# Create UDF for use in Spark
get_audio_duration_udf = udf(get_audio_duration, FloatType())

# COMMAND ----------

# DBTITLE 1,Filename Parsing Functions

def parse_call_id_from_filename(filename: str) -> str:
    """
    Extract call_id from filename.

    Expected pattern: {call_id}_{agent_id}_{datetime}.{ext}

    Args:
        filename: Name of the audio file

    Returns:
        call_id string
    """
    try:
        # Remove extension first
        base_name = os.path.splitext(filename)[0]
        parts = base_name.split('_')
        return parts[0] if len(parts) > 0 else None
    except Exception as e:
        print(f"⚠️ Error parsing call_id from {filename}: {e}")
        return None


def parse_agent_id_from_filename(filename: str) -> str:
    """
    Extract agent_id from filename.

    Expected pattern: {call_id}_{agent_id}_{datetime}.{ext}

    Args:
        filename: Name of the audio file

    Returns:
        agent_id string
    """
    try:
        base_name = os.path.splitext(filename)[0]
        parts = base_name.split('_')
        return parts[1] if len(parts) > 1 else None
    except Exception as e:
        print(f"⚠️ Error parsing agent_id from {filename}: {e}")
        return None


def parse_datetime_from_filename(filename: str) -> str:
    """
    Extract datetime from filename and convert to timestamp format.

    Expected pattern: {call_id}_{agent_id}_{YYYY-MM-DD_HH-MM-SS}.{ext}

    Args:
        filename: Name of the audio file

    Returns:
        Datetime string in format 'YYYY-MM-DD HH:MM:SS'
    """
    try:
        base_name = os.path.splitext(filename)[0]
        parts = base_name.split('_')

        if len(parts) >= 5:
            # Extract date and time parts
            date_part = parts[2]  # YYYY-MM-DD
            time_part = '_'.join(parts[3:])  # HH-MM-SS (might have more underscores)
            time_part = time_part.replace('_', ':').replace('-', ':')  # Convert to HH:MM:SS

            # Combine date and time
            datetime_str = f"{date_part} {time_part}"
            return datetime_str
        else:
            print(f"⚠️ Filename doesn't match expected pattern: {filename}")
            return None
    except Exception as e:
        print(f"⚠️ Error parsing datetime from {filename}: {e}")
        return None


# Create UDFs for use in Spark
parse_call_id_udf = udf(parse_call_id_from_filename, StringType())
parse_agent_id_udf = udf(parse_agent_id_from_filename, StringType())
parse_datetime_udf = udf(parse_datetime_from_filename, StringType())

# COMMAND ----------

# DBTITLE 1,Filename Parsing with PySpark Functions (Alternative)

def parse_filename_metadata(df):
    """
    Parse filename to extract call metadata using PySpark functions.

    This is an alternative approach using built-in PySpark functions
    which is more efficient than UDFs.

    Expected filename pattern: {call_id}_{agent_id}_{YYYY-MM-DD_HH-MM-SS}.{ext}

    Args:
        df: DataFrame with 'path' column

    Returns:
        DataFrame with additional columns: file_name, call_id, agent_id, call_datetime
    """
    # Extract filename from path
    df = df.withColumn("file_name", regexp_extract(col("path"), r"([^/]+)$", 1))

    # Remove extension
    df = df.withColumn("file_name_base", regexp_replace(col("file_name"), r"\.[^.]+$", ""))

    # Extract call_id (first part before underscore)
    df = df.withColumn("call_id", split(col("file_name_base"), "_").getItem(0))

    # Extract agent_id (second part)
    df = df.withColumn("agent_id", split(col("file_name_base"), "_").getItem(1))

    # Extract datetime (third part onwards: YYYY-MM-DD_HH-MM-SS)
    # Build datetime string from parts
    df = df.withColumn("date_part", split(col("file_name_base"), "_").getItem(2))
    df = df.withColumn("time_part_1", split(col("file_name_base"), "_").getItem(3))
    df = df.withColumn("time_part_2", split(col("file_name_base"), "_").getItem(4))

    # Combine and convert to timestamp format
    df = df.withColumn(
        "datetime_str",
        concat_ws(
            " ",
            col("date_part"),
            concat_ws(":", col("time_part_1"), col("time_part_2"), split(col("file_name_base"), "_").getItem(5))
        )
    )

    # Convert to timestamp
    df = df.withColumn("call_datetime", to_timestamp(col("datetime_str"), "yyyy-MM-dd HH:mm:ss"))

    # Drop intermediate columns
    df = df.drop("file_name_base", "date_part", "time_part_1", "time_part_2", "datetime_str")

    return df

# COMMAND ----------

# DBTITLE 1,Audio Format Detection

def detect_audio_format(file_path: str) -> str:
    """
    Detect audio file format.

    Args:
        file_path: Full path to the audio file

    Returns:
        Format string (e.g., 'mp3', 'wav', 'flac'), or 'unknown'
    """
    try:
        audio = MutagenFile(file_path)

        if audio is None:
            return "unknown"

        # Get MIME type or class name
        if hasattr(audio, 'mime'):
            mime_type = audio.mime[0] if isinstance(audio.mime, list) else audio.mime
            return mime_type.split('/')[-1]  # Extract format from MIME type
        else:
            # Fallback to file extension
            _, ext = os.path.splitext(file_path)
            return ext.lstrip('.').lower()

    except Exception as e:
        print(f"⚠️ Error detecting format for {file_path}: {e}")
        return "unknown"


detect_audio_format_udf = udf(detect_audio_format, StringType())

# COMMAND ----------

# DBTITLE 1,Test Functions (Optional)

def test_parsing():
    """
    Test the filename parsing functions with sample filenames.
    """
    test_files = [
        "ABC123_AGT001_2024-01-15_10-30-45.wav",
        "XYZ789_AGT002_2024-02-20_14-22-10.mp3",
        "DEF456_AGT003_2024-03-05_09-15-30.flac"
    ]

    print("Testing filename parsing functions:")
    print("=" * 80)

    for filename in test_files:
        call_id = parse_call_id_from_filename(filename)
        agent_id = parse_agent_id_from_filename(filename)
        datetime_str = parse_datetime_from_filename(filename)

        print(f"\nFilename: {filename}")
        print(f"  Call ID:    {call_id}")
        print(f"  Agent ID:   {agent_id}")
        print(f"  Datetime:   {datetime_str}")

    print("\n" + "=" * 80)

# Uncomment to run tests
# test_parsing()

# COMMAND ----------

# DBTITLE 1,Module Summary

print("""
Audio Processing Utilities - Available Functions:
==================================================

1. get_audio_duration(file_path) -> float
   - Extract audio duration in seconds using mutagen
   - Also available as UDF: get_audio_duration_udf

2. parse_call_id_from_filename(filename) -> str
   - Extract call_id from filename
   - Also available as UDF: parse_call_id_udf

3. parse_agent_id_from_filename(filename) -> str
   - Extract agent_id from filename
   - Also available as UDF: parse_agent_id_udf

4. parse_datetime_from_filename(filename) -> str
   - Extract datetime from filename
   - Also available as UDF: parse_datetime_udf

5. parse_filename_metadata(df) -> DataFrame
   - Parse all metadata from filename using PySpark functions
   - More efficient than UDFs for large datasets

6. detect_audio_format(file_path) -> str
   - Detect audio file format
   - Also available as UDF: detect_audio_format_udf

Expected filename pattern:
  {call_id}_{agent_id}_{YYYY-MM-DD_HH-MM-SS}.{ext}
  Example: ABC123_AGT001_2024-01-15_10-30-45.wav
""")
