"""
Loads data source for the application.
Currently supported:
    - .csv 
    - InterSystems globals through global mapping
"""
import pandas as pd
import streamlit as st
import duckdb
import pyodbc
from config import (
    DataSource,
    DATA_SOURCE_TYPE,
    CSV_PATH,
    IRIS_CONFIG,
    IRIS_TABLE,
    DATA_SOURCE_METADATA
)

class DataSourceManager:
    
    def __init__(self):
        self.source_type = DATA_SOURCE_TYPE
        self.metadata = DATA_SOURCE_METADATA[DATA_SOURCE_TYPE]
    
    @st.cache_data(ttl=3600)
    def load(_self) -> pd.DataFrame:
        """Load data from configured source."""
        if _self.source_type == DataSource.CSV:
            return pd.read_csv(CSV_PATH)
        
        elif _self.source_type == DataSource.IRIS:
            connection_string = (
                f"DRIVER={IRIS_CONFIG['DRIVER']};"
                f"SERVER={IRIS_CONFIG['SERVER']};"
                f"PORT={IRIS_CONFIG['PORT']};"
                f"DATABASE={IRIS_CONFIG['DATABASE']};"
                f"UID={IRIS_CONFIG['UID']};"
                f"PWD={IRIS_CONFIG['PWD']};"
            )
            
            with st.spinner(f"🔄 Loading data from {IRIS_TABLE}..."):
                conn = pyodbc.connect(connection_string)
                
                last_week = 5836924800
                
                df = pd.read_sql(f"""
                    SELECT TOP 500000 * 
                    FROM {IRIS_TABLE}
                    WHERE Timestamp > {last_week}
                    ORDER BY ID DESC
                """, conn)
                
                conn.close()
            
            st.toast(f"✅ Loaded {len(df):,} rows!", icon="✅")
            return df
    
    def get_schema(self, df: pd.DataFrame) -> dict:
        """Get schema from loaded DataFrame (dynamic)."""
        return {
            "columns": list(df.columns),
            "types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "row_count": len(df),
            "column_count": len(df.columns)
        }
    
    def get_sample(self, df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
        """Get sample rows."""
        return df.head(n)


@st.cache_resource
def init_duckdb():
    """Initialize DuckDB in-memory connection."""
    return duckdb.connect(':memory:')