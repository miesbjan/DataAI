# app.py
import streamlit as st
from core.state import AppState
from core.data_manager import DataSourceManager, init_duckdb
from core.ai_manager import AIService
from core.code_executor import CodeExecutor
from core.context_manager import ContextManager
from core.query_library import QueryLibrary
from utils.helper import (
    handle_code_mode,
    handle_natural_language
)
from config import DEFAULT_APP_MODE

def main():
    st.set_page_config(page_title="Data Analysis Chatbot", layout="wide")
    
    # Initialize components
    state = AppState()
    data_source = DataSourceManager()
    ai_service = AIService()
    executor = CodeExecutor()
    context_manager = ContextManager()
    query_library = QueryLibrary()
    
    # Load data if needed
    if not state.is_data_loaded():
        state.df = data_source.load()
        state.conn = init_duckdb()
        state.schema = data_source.get_schema(state.df)
    
    # Title
    st.title("💬 Data Analysis Chatbot")
    
    # Mode selector
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💬 Natural", type="primary" if state.current_mode == "natural" else "secondary"):
            state.set_mode("natural")
            st.rerun()
    with col2:
        if st.button("📊 SQL", type="primary" if state.current_mode == "sql" else "secondary"):
            state.set_mode("sql")
            st.rerun()
    with col3:
        if st.button("🐍 Python", type="primary" if state.current_mode == "python" else "secondary"):
            state.set_mode("python")
            st.rerun()
    
    # Chat input
    placeholder = {
        "natural": "Ask a question...",
        "sql": "Write SQL or ask in natural language...",
        "python": "Write Python or ask in natural language..."
    }
    
    if user_input := st.chat_input(placeholder[state.current_mode]):
        if state.current_mode == "natural":
            from config import DEFAULT_SYSTEM_PROMPT
            handle_natural_language(user_input, state, ai_service, context_manager, DEFAULT_SYSTEM_PROMPT)
        else:
            handle_code_mode(state.current_mode, user_input, state, ai_service, executor, context_manager)

if __name__ == "__main__":
    main()