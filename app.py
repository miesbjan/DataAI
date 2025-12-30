"""
Main application file - orchestrates all components
"""
import streamlit as st
from core.state import AppState
from core.data_manager import DataSourceManager, init_duckdb
from core.ai_manager import AIService
from core.code_executor import CodeExecutor
from core.context_manager import ContextManager
from core.query_library import QueryLibrary
from ui import render_sidebar, render_chat_history, render_compact_mode_selector
from utils.helper import handle_code_mode, handle_code_rerun, handle_natural_language
from config import DEFAULT_APP_MODE, get_active_metadata


def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="Data Analysis Chatbot",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize components
    state = AppState()
    data_source = DataSourceManager()
    ai_service = AIService()
    executor = CodeExecutor()
    context_manager = ContextManager()
    query_library = QueryLibrary()
    
    # Load data if needed
    if not state.is_data_loaded():
        with st.spinner("Loading data..."):
            state.df = data_source.load()
            state.conn = init_duckdb()
            state.schema = data_source.get_schema(state.df)

    handle_code_rerun(state, executor, context_manager)
    
    # Render sidebar
    render_sidebar(state, data_source, query_library)
    
    # Main area
    st.title("💬 Data Analysis Chatbot")
    
    # Handle loaded query from sidebar
    handle_loaded_query(state, context_manager, executor, query_library)
    
    # Render chat history
    render_chat_history(state)
    
    # Chat input with compact mode selector
    render_input_area(state, ai_service, executor, context_manager)


def handle_loaded_query(state, context_manager, executor, query_library):
    """
    Handle query loaded from query library.

    Args:
        state: AppState instance
        context_manager: ContextManager instance
        executor: CodeExecutor instance
        query_library: QueryLibrary instance
    """
    if st.session_state.get('load_query_id'):
        query = query_library.load(st.session_state.load_query_id)

        if query:
            # Set mode
            state.set_mode(query['mode'])

            # Display user message
            with st.chat_message("user"):
                st.markdown(f"*Loading saved query: {query['name']}*")

            # Add to context
            context_manager.add_user_message(f"Loaded: {query['name']}", query['mode'])

            # Execute using shared handler
            from utils.helper import handle_direct_code_execution
            handle_direct_code_execution(
                code=query['code'],
                mode=query['mode'],
                state=state,
                executor=executor,
                context_manager=context_manager,
                caption=f"⚡ Executing saved query: {query['name']}",
                source="saved"
            )

        # Clear trigger
        st.session_state.load_query_id = None


def render_input_area(state, ai_service, executor, context_manager):
    """
    Render chat input area with compact mode selector.
    
    Args:
        state: AppState instance
        ai_service: AIService instance
        executor: CodeExecutor instance
        context_manager: ContextManager instance
    """
    # Create columns for input and mode selector
    col_input, col_mode = st.columns([4, 1])
    
    with col_mode:
        # Compact mode selector
        current_mode = render_compact_mode_selector(state)
    
    with col_input:
        # Dynamic placeholder based on mode
        placeholders = {
            "natural": "Ask a question about your data...",
            "sql": "Write SQL or ask in natural language...",
            "python": "Write Python code or ask in natural language..."
        }
        
        placeholder = placeholders.get(state.current_mode, "Ask a question...")
        
        # Chat input
        user_input = st.chat_input(placeholder)
    
    # Handle input
    if user_input:
        if state.current_mode == "natural":

            from core.prompts import build_natural_language_prompt
            meta = get_active_metadata()
            system_prompt = build_natural_language_prompt(meta)
            
            handle_natural_language(
                user_input,
                state,
                ai_service,
                context_manager,
                system_prompt
            )
        else:
            # SQL or Python mode
            handle_code_mode(
                state.current_mode,
                user_input,
                state,
                ai_service,
                executor,
                context_manager
            )


if __name__ == "__main__":
    main()