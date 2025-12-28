import streamlit as st

# --- AI API Keys ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

# --- Models Configuration ---
MODEL_CHEAP = "gpt-5-nano"
MODEL_MEDIUM = "gpt-5-mini"
MODEL_SMART = "gpt-5.2"

# Pricing (per 1M tokens)
MODEL_PRICING = {
    "gpt-5-nano": {
        "input": 0.05,
        "output": 0.40
    },
    "gpt-5-mini": {
        "input": 0.25,
        "output": 2.00
    },
    "gpt-5.2": {
        "input": 1.75,
        "output": 14.00
    }
}

# --- Data Source Configuration ---
class DataSource:
    CSV = "csv"
    IRIS = "iris"

DATA_SOURCE_TYPE = DataSource.CSV

CSV_PATH = "./data/out.c_mart.mart_results_v1.3.csv"
IRIS_CONFIG = {}
IRIS_TABLE = "SQLUser.Vehicle"

DATA_SOURCE_METADATA = {
    DataSource.CSV: {
        "name": "mart_results_v1",
        "display_name": "Endurance Sports Athletes",
        "table_name": "df",
    },
    DataSource.IRIS: {
        "name": "SQLUser.Vehicle",
        "display_name": "DISPECINK Vehicles",
        "table_name": "df",
    }
}

def get_active_metadata():
    """
    Get metadata for the currently active data source.
    
    Returns:
        dict: Metadata for active source
    """
    return DATA_SOURCE_METADATA[DATA_SOURCE_TYPE]

# --- Application Configuration ---
class AppMode:
    NATURAL_LANGUAGE = "natural"
    SQL = "sql",
    PYTHON = "python"

DEFAULT_APP_MODE = AppMode.NATURAL_LANGUAGE