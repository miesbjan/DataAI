"""
Helper functions for app.py
Contains input detection, handlers, and display functions
"""
import streamlit as st
import pandas as pd
from core.ai_manager import GenerationMetadata
from ui.chat import render_sql_result, render_python_result


# ========== Input Type Detection ==========

def is_raw_sql(text: str) -> bool:
    """
    Detect if input is raw SQL code rather than natural language.
    """
    text_stripped = text.strip().upper()

    return text_stripped.startswith('SELECT')

def is_raw_python(text: str) -> bool:
    """
    Detect if input is raw Python code rather than natural language.
    Optimized for data analysis use cases.
    """
    if not text:
        return False

    t = text.strip()

    # Common Python statement starts
    python_starts = (
        "import ", "from ", "def ", "class ",
        "for ", "while ", "if ", "elif ", "else:",
        "try:", "except", "with ",
        "return ", "print("
    )

    return t.startswith(python_starts)


# ========== Code Mode Handler ==========

def handle_code_mode(
    mode: str,
    user_input: str,
    state,
    ai_service,
    executor,
    context_manager,
    max_attempts: int = 2
):
    """
    Handle SQL/Python code generation and execution with retry on error.
    
    Args:
        mode: "sql" or "python"
        user_input: User's query or code
        state: AppState instance
        ai_service: AIService instance
        executor: CodeExecutor instance
        context_manager: ContextManager instance
        max_attempts: Maximum retry attempts (default 2)
    """
    # Add user message to context
    context_manager.add_user_message(user_input, mode)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Add to display messages
    state.display_messages.append({
        "role": "user",
        "content": user_input,
        "mode": mode
    })
    
    # Display assistant response
    with st.chat_message("assistant"):
        # Detect if raw code or natural language
        is_raw = is_raw_sql(user_input) if mode == "sql" else is_raw_python(user_input)
        
        if is_raw:
            # User wrote code directly - no retry for direct code
            code = user_input.strip()
            metadata = GenerationMetadata(
                model="none",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                source="direct"
            )
            st.caption("⚡ Executing direct code")
            
            # Execute once (no retry for user code)
            if mode == "sql":
                result, error = executor.execute_sql(state.conn, state.df, code)
            else:
                result, error = executor.execute_python(state.conn, state.df, code)
            
            # Handle result
            if error:
                st.error(error)
                context_manager.add_error(code, error, mode)
                state.display_messages.append({
                    "role": "assistant",
                    "content": f"Error: {error}",
                    "mode": mode,
                    "executed_code": code,
                    "code_language": mode,
                    "source": "direct",
                    "error": error
                })
                return  # ← Stop here for user code
            
        else:
            # AI-generated code - try with retry
            attempt = 1
            error_context = None
            
            while attempt <= max_attempts:
                # Generate code
                context = context_manager.get_context_for_ai()
                
                if mode == "sql":
                    code, metadata = ai_service.generate_sql(
                        user_input, 
                        state.df, 
                        context, 
                        error_context=error_context
                    )
                else:
                    code, metadata = ai_service.generate_python(
                        user_input, 
                        state.df, 
                        context, 
                        error_context=error_context
                    )
                
                # Show generation info
                if attempt == 1:
                    st.caption(f"🤖 Generated with **{metadata.model}** • Cost: **${metadata.cost:.5f}**")
                else:
                    st.caption(f"🔄 Retry {attempt}/{max_attempts} with **{metadata.model}** • Cost: **${metadata.cost:.5f}**")
                
                # Display code
                st.code(code, language=mode)
                
                # Execute
                if mode == "sql":
                    result, error = executor.execute_sql(state.conn, state.df, code)
                else:
                    result, error = executor.execute_python(state.conn, state.df, code)
                
                # Check result
                if error:
                    # Show error
                    st.error(f"❌ Attempt {attempt} failed: {error}")
                    
                    # Prepare for retry
                    if attempt < max_attempts:
                        st.info(f"🔄 Attempting to fix and retry...")
                        error_context = {
                            "failed_query": code,
                            "error": error
                        }
                        attempt += 1
                        
                        # Update costs for retry
                        state.total_cost += metadata.cost
                        state.api_calls += 1
                        if metadata.cost > 0:
                            state.cost_history.append({
                                "model": metadata.model,
                                "cost": metadata.cost,
                                "input_tokens": metadata.input_tokens,
                                "output_tokens": metadata.output_tokens,
                                "mode": mode
                            })
                        
                        continue  # ← Retry!
                    else:
                        # Max attempts reached
                        st.error(f"❌ Failed after {max_attempts} attempts")
                        st.error(error)
                        context_manager.add_error(code, error, mode)
                        
                        state.display_messages.append({
                            "role": "assistant",
                            "content": f"Error after {max_attempts} attempts: {error}",
                            "mode": mode,
                            "executed_code": code,
                            "code_language": mode,
                            "source": metadata.source,
                            "error": error
                        })
                        
                        # Update costs for final failed attempt
                        state.total_cost += metadata.cost
                        state.api_calls += 1
                        if metadata.cost > 0:
                            state.cost_history.append({
                                "model": metadata.model,
                                "cost": metadata.cost,
                                "input_tokens": metadata.input_tokens,
                                "output_tokens": metadata.output_tokens,
                                "mode": mode
                            })
                        
                        return  # ← Stop after max attempts
                
                else:
                    # Success! Break retry loop
                    if attempt > 1:
                        st.success(f"✅ Succeeded on attempt {attempt}!")
                    break
        
        # ===== SUCCESS PATH =====
        # Display result
        if mode == "sql":
            message_dict = {
                "dataframe": result
            }
            render_sql_result(message_dict)
            context_manager.add_sql_result(code, result)
            
            # Add to display messages
            state.display_messages.append({
                "role": "assistant",
                "content": "SQL query executed",
                "mode": "sql",
                "executed_code": code,
                "code_language": "sql",
                "dataframe": result,
                "model": metadata.model,
                "cost": metadata.cost,
                "source": metadata.source
            })
            
        else:
            message_dict = {
                "python_output": result.get('output'),
                "chart": result.get('fig'),
                "namespace": result.get('namespace')
            }
            render_python_result(message_dict)
            context_manager.add_python_result(code, result)
            
            # Add to display messages
            state.display_messages.append({
                "role": "assistant",
                "content": "Python code executed",
                "mode": "python",
                "executed_code": code,
                "code_language": "python",
                "python_output": result.get('output'),
                "chart": result.get('fig'),
                "namespace": result.get('namespace'),
                "model": metadata.model,
                "cost": metadata.cost,
                "source": metadata.source
            })
        
        # ===== SAVE BUTTON =====
        st.divider()
        
        # Save button
        if st.button("💾 Save Query", key=f"save_current_{hash(code)}"):
            st.session_state.show_save_dialog_current = True
            st.rerun()
        
        # Show save dialog if triggered
        if st.session_state.get("show_save_dialog_current"):
            from ui.chat import render_save_dialog_inline
            render_save_dialog_inline(code, mode, state)
        
        # Update state costs
        state.total_cost += metadata.cost
        state.api_calls += 1
        if metadata.cost > 0:
            state.cost_history.append({
                "model": metadata.model,
                "cost": metadata.cost,
                "input_tokens": metadata.input_tokens,
                "output_tokens": metadata.output_tokens,
                "mode": mode
            })


# ========== Natural Language Handler ==========

def handle_natural_language(
    user_input: str,
    state,
    ai_service,
    context_manager,
    system_prompt: str
):
    """
    Handle natural language conversational mode.
    
    Args:
        user_input: User's question
        state: AppState instance
        ai_service: AIService instance
        context_manager: ContextManager instance
        system_prompt: System prompt for conversation
    """
    # Add user message
    context_manager.add_user_message(user_input, "natural")
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Display assistant response
    with st.chat_message("assistant"):
        context = context_manager.get_context_for_ai()
        
        # Generate response (streaming)
        response_stream, metadata = ai_service.generate_text(
            user_input,
            context,
            system_prompt
        )
        
        # Display streaming response
        message_placeholder = st.empty()
        full_response = ""
        
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
        
        # Store in display messages
        state.display_messages.append({
            "role": "assistant",
            "content": full_response,
            "mode": "natural"
        })


def handle_code_rerun(state, executor, context_manager):
    """
    Handle re-execution of edited code from chat history.
    
    Args:
        state: AppState instance
        executor: CodeExecutor instance
        context_manager: ContextManager instance
    """
    # Check for any rerun triggers
    for key in list(st.session_state.keys()):
        if key.startswith("rerun_code_"):
            idx = int(key.split("_")[-1])
            edited_code = st.session_state[key]
            
            # Get original message
            if idx < len(state.display_messages):
                original_msg = state.display_messages[idx]
                mode = original_msg.get("mode")
                
                # Execute edited code
                with st.chat_message("assistant"):
                    st.caption("⚡ Executing edited code")
                    st.code(edited_code, language=mode)
                    
                    if mode == "sql":
                        result, error = executor.execute_sql(state.conn, state.df, edited_code)
                        
                        if error:
                            st.error(f"❌ Error: {error}")
                            context_manager.add_error(edited_code, error, mode)
                        else:
                            st.dataframe(result, use_container_width=True)
                            st.caption(f"✅ {len(result):,} rows")
                            context_manager.add_sql_result(edited_code, result)
                            
                            # Add new message with edited result
                            state.display_messages.append({
                                "role": "assistant",
                                "content": "Re-executed edited SQL",
                                "mode": "sql",
                                "executed_code": edited_code,
                                "code_language": "sql",
                                "dataframe": result,
                                "source": "edited"
                            })
                    
                    elif mode == "python":
                        result, error = executor.execute_python(state.conn, state.df, edited_code)
                        
                        if error:
                            st.error(f"❌ Error: {error}")
                            context_manager.add_error(edited_code, error, mode)
                        else:
                            if result.get('output'):
                                with st.expander("📄 Console Output", expanded=True):
                                    st.text(result['output'])
                            
                            if result.get('fig'):
                                st.plotly_chart(result['fig'], use_container_width=True)
                            
                            context_manager.add_python_result(edited_code, result)
                            
                            # Add new message with edited result
                            state.display_messages.append({
                                "role": "assistant",
                                "content": "Re-executed edited Python",
                                "mode": "python",
                                "executed_code": edited_code,
                                "code_language": "python",
                                "python_output": result.get('output'),
                                "chart": result.get('fig'),
                                "source": "edited"
                            })
            
            # Clear trigger
            del st.session_state[key]
            st.rerun()