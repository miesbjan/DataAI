"""
Chat interface components for displaying messages and handling input
"""
import streamlit as st
from config import get_active_metadata
from utils.helper import handle_natural_language, handle_code_mode


def render_chat_history(state):
    """
    Render all chat messages from history.
    
    Args:
        state: AppState instance
    """
    for idx, message in enumerate(state.display_messages):
        if message["role"] == "user":
            render_user_message(message)
        elif message["role"] == "assistant":
            render_assistant_message(message, idx, state)


def render_user_message(message: dict):
    """
    Render a user message.
    
    Args:
        message: Message dict
    """
    with st.chat_message("user"):
        st.markdown(message["content"])


def render_assistant_message(message: dict, idx: int, state):
    """
    Render an assistant message with code, results, and save button.
    
    Args:
        message: Message dict
        idx: Message index
        state: AppState instance
    """
    with st.chat_message("assistant"):
        # Mode indicator
        mode = message.get("mode", "natural")
        
        if mode == "natural":
            # Natural language response (simple)
            st.markdown(message.get("content", ""))
        else:
            # Code mode (SQL/Python)
            render_code_result(message, idx, mode, state)


def render_code_result(message: dict, idx: int, mode: str, state):
    """
    Render code execution result with editable code.
    
    Args:
        message: Message dict
        idx: Message index
        mode: "sql" or "python"
        state: AppState instance
    """
    from core.code_executor import CodeExecutor
    
    # Metadata (model, cost)
    if message.get("source") == "generated":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"🤖 Generated with **{message.get('model', 'unknown')}**")
        with col2:
            if message.get('cost'):
                st.caption(f"💰 ${message['cost']:.5f}")
    elif message.get("source") == "direct":
        st.caption("⚡ Direct execution")
    elif message.get("source") == "edited":
        st.caption("✏️ Edited and re-executed")
    
    # Editable code
    if message.get("executed_code"):
        with st.expander(f"📝 {mode.upper()} Code (Click to edit)", expanded=True):
            # Editable text area
            edited_code = st.text_area(
                "Edit code",
                value=message["executed_code"],
                height=200,
                key=f"code_edit_{idx}",
                label_visibility="collapsed"
            )
            
            # Re-run button
            if st.button(f"▶️ Run Edited Code", key=f"rerun_{idx}"):
                executor = CodeExecutor()
                
                # Execute edited code
                if mode == "sql":
                    result, error = executor.execute_sql(state.conn, state.df, edited_code)
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                        # Update message with error
                        state.display_messages[idx]["executed_code"] = edited_code
                        state.display_messages[idx]["error"] = error
                        state.display_messages[idx]["source"] = "edited"
                    else:
                        # Update message with new results
                        state.display_messages[idx]["executed_code"] = edited_code
                        state.display_messages[idx]["dataframe"] = result
                        state.display_messages[idx]["source"] = "edited"
                        state.display_messages[idx].pop("error", None)  # Remove error if existed
                        st.success(f"✅ Updated! {len(result):,} rows")
                
                elif mode == "python":
                    result, error = executor.execute_python(state.conn, state.df, edited_code)
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                        # Update message with error
                        state.display_messages[idx]["executed_code"] = edited_code
                        state.display_messages[idx]["error"] = error
                        state.display_messages[idx]["source"] = "edited"
                    else:
                        # Update message with new results
                        state.display_messages[idx]["executed_code"] = edited_code
                        state.display_messages[idx]["python_output"] = result.get('output')
                        state.display_messages[idx]["chart"] = result.get('fig')
                        state.display_messages[idx]["namespace"] = result.get('namespace')
                        state.display_messages[idx]["source"] = "edited"
                        state.display_messages[idx].pop("error", None)  # Remove error if existed
                        st.success("✅ Updated!")
                
                # Rerun to show updated results
                st.rerun()
    
    # Show error if exists
    if message.get("error"):
        st.error(f"❌ Error: {message['error']}")
        return  # Don't show results if there's an error
    
    # Results
    if mode == "sql":
        render_sql_result(message)
    elif mode == "python":
        render_python_result(message)
    
    # Save button
    render_save_button(message, idx, state)


def render_sql_result(message: dict):
    """
    Render SQL query results.
    
    Args:
        message: Message dict with 'dataframe'
    """
    if "dataframe" in message:
        df = message["dataframe"]
        st.dataframe(df, use_container_width=True)
        
        # Row count
        row_count = len(df)
        if row_count == 1:
            st.caption("✅ 1 row")
        else:
            st.caption(f"✅ {row_count:,} rows")


def render_python_result(message: dict):
    """
    Render Python execution results.
    
    Args:
        message: Message dict with 'python_output', 'chart', 'dataframe'
    """
    # Console output
    if message.get("python_output"):
        with st.expander("📄 Console Output", expanded=True):
            st.text(message["python_output"])
    
    # Chart
    if message.get("chart"):
        st.plotly_chart(message["chart"], use_container_width=True)
    
    # DataFrame
    if message.get("dataframe"):
        st.dataframe(message["dataframe"], use_container_width=True)
    
    # Success message if no output
    if not any([message.get("python_output"), message.get("chart"), message.get("dataframe")]):
        st.caption("✅ Code executed successfully")


def render_save_button(message: dict, idx: int, state):
    """
    Render save query button and dialog.
    
    Args:
        message: Message dict
        idx: Message index
        state: AppState instance
    """
    # Only show save button for executed code
    if not message.get("executed_code"):
        return
    
    # Save button
    if st.button("💾 Save Query", key=f"save_query_{idx}"):
        st.session_state.show_save_dialog = idx
        st.rerun()
    
    # Save dialog
    if st.session_state.get("show_save_dialog") == idx:
        render_save_dialog(message, state)


def render_save_dialog(message: dict, state):
    """
    Render dialog to save query.
    
    Args:
        message: Message dict
        state: AppState instance
    """
    with st.form(key=f"save_form_{message.get('executed_code', '')[:10]}"):
        st.write("**💾 Save this query**")
        
        name = st.text_input("Query Name", f"Query {len(state.display_messages)}")
        description = st.text_area("Description (optional)", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("Save", use_container_width=True):
                from core.query_library import QueryLibrary
                query_library = QueryLibrary()
                
                query_library.save(
                    name=name,
                    code=message["executed_code"],
                    mode=message["mode"],
                    description=description
                )
                
                st.session_state.show_save_dialog = None
                st.success(f"✅ Saved '{name}'!")
                st.rerun()
        
        with col2:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.show_save_dialog = None
                st.rerun()


def render_compact_mode_selector(state):
    """
    Render compact inline mode selector.
    Returns selected mode string.
    
    Args:
        state: AppState instance
    
    Returns:
        str: Selected mode ("natural", "sql", or "python")
    """
    # Map display to internal values
    mode_options = {
        "💬 Natural Language": "natural",
        "📊 SQL": "sql",
        "🐍 Python": "python"
    }
    
    # Reverse map for default
    reverse_map = {v: k for k, v in mode_options.items()}
    current_display = reverse_map.get(state.current_mode, "💬 Natural Language")
    
    # Dropdown
    selected_display = st.selectbox(
        "Mode",
        list(mode_options.keys()),
        index=list(mode_options.keys()).index(current_display),
        label_visibility="collapsed",
        key="mode_selector_compact"
    )
    
    selected_mode = mode_options[selected_display]
    
    # Update state if changed
    if selected_mode != state.current_mode:
        state.set_mode(selected_mode)
    
    return selected_mode

def render_save_dialog_inline(code: str, mode: str, state):
    """
    Render inline save dialog for current execution.
    Can be used both in chat history and live execution.
    
    Args:
        code: Code to save
        mode: "sql" or "python"
        state: AppState instance
    """
    with st.form(key=f"save_form_{hash(code)}", clear_on_submit=True):
        st.write("**💾 Save this query**")
        
        name = st.text_input("Query Name", f"Query {len(state.display_messages)}")
        description = st.text_area("Description (optional)", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Save", use_container_width=True):
                from core.query_library import QueryLibrary
                query_library = QueryLibrary()
                
                query_library.save(
                    name=name,
                    code=code,
                    mode=mode,
                    description=description
                )
                
                st.session_state.show_save_dialog_current = False
                st.success(f"✅ Saved '{name}'!")
                st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.show_save_dialog_current = False
                st.rerun()

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