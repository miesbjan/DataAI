"""
Application state management
"""
import streamlit as st
import pandas as pd
from typing import Optional
from config import DEFAULT_APP_MODE

class AppState:
    """Central state manager for the application"""
    
    def __init__(self):
        """Initialize application state"""
        # Initialize session state if not exists
        if "app_state" not in st.session_state:
            st.session_state.app_state = {
                # Data layer
                "df": None,
                "conn": None,
                "schema": None,
                
                # Mode layer
                "current_mode": DEFAULT_APP_MODE,
                
                # Conversation layer
                "display_messages": [],
                
                # Cost tracking layer
                "total_cost": 0.0,
                "api_calls": 0,
                "cost_history": []
            }
    
    # ========== Data Layer Properties ==========
    
    @property
    def df(self) -> Optional[pd.DataFrame]:
        """Get loaded DataFrame"""
        return st.session_state.app_state["df"]
    
    @df.setter
    def df(self, value: Optional[pd.DataFrame]):
        """Set loaded DataFrame"""
        st.session_state.app_state["df"] = value
    
    @property
    def conn(self):
        """Get DuckDB connection"""
        return st.session_state.app_state["conn"]
    
    @conn.setter
    def conn(self, value):
        """Set DuckDB connection"""
        st.session_state.app_state["conn"] = value
    
    @property
    def schema(self) -> Optional[dict]:
        """Get data schema"""
        return st.session_state.app_state["schema"]
    
    @schema.setter
    def schema(self, value: Optional[dict]):
        """Set data schema"""
        st.session_state.app_state["schema"] = value
    
    # ========== Mode Layer Properties ==========
    
    @property
    def current_mode(self) -> str:
        """Get current mode"""
        return st.session_state.app_state["current_mode"]
    
    @current_mode.setter
    def current_mode(self, value: str):
        """Set current mode"""
        st.session_state.app_state["current_mode"] = value
    
    # ========== Conversation Layer Properties ==========
    
    @property
    def display_messages(self) -> list:
        """Get display messages (for UI)"""
        return st.session_state.app_state["display_messages"]
    
    @display_messages.setter
    def display_messages(self, value: list):
        """Set display messages"""
        st.session_state.app_state["display_messages"] = value
    
    # ========== Cost Tracking Properties ==========
    
    @property
    def total_cost(self) -> float:
        """Get total API cost"""
        return st.session_state.app_state["total_cost"]
    
    @total_cost.setter
    def total_cost(self, value: float):
        """Set total API cost"""
        st.session_state.app_state["total_cost"] = value
    
    @property
    def api_calls(self) -> int:
        """Get number of API calls"""
        return st.session_state.app_state["api_calls"]
    
    @api_calls.setter
    def api_calls(self, value: int):
        """Set number of API calls"""
        st.session_state.app_state["api_calls"] = value
    
    @property
    def cost_history(self) -> list:
        """Get cost history"""
        return st.session_state.app_state["cost_history"]
    
    @cost_history.setter
    def cost_history(self, value: list):
        """Set cost history"""
        st.session_state.app_state["cost_history"] = value
    
    # ========== Methods ==========
    
    def get_mode(self) -> str:
        """
        Get current mode.
        
        Returns:
            str: Current mode
        """
        return self.current_mode
    
    def set_mode(self, mode: str):
        """
        Set current mode.
        
        Args:
            mode: New mode to set
        """
        valid_modes = ["natural", "sql", "python"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")
        self.current_mode = mode
    
    def is_data_loaded(self) -> bool:
        """
        Check if data is loaded.
        
        Returns:
            bool: True if DataFrame is loaded
        """
        return self.df is not None
    
    def reset(self):
        """
        Reset conversation and cost tracking.
        Keeps data, connection, and mode.
        """
        self.display_messages = []
        self.total_cost = 0.0
        self.api_calls = 0
        self.cost_history = []
    
    def clear_all(self):
        """
        Clear all state (full reset).
        """
        st.session_state.app_state = {
            "df": None,
            "conn": None,
            "schema": None,
            "current_mode": DEFAULT_MODE,
            "display_messages": [],
            "total_cost": 0.0,
            "api_calls": 0,
            "cost_history": []
        }