"""
Context management for AI conversations
Manages conversation history and formats results compactly for AI context
"""
import pandas as pd


class ContextManager:
    """Manages conversation context for AI interactions"""
    
    # Token management constants
    MAX_MESSAGE_LENGTH = 500  # Max chars per message (~200 tokens)
    DEFAULT_CONTEXT_LIMIT = 5  # Number of messages to return by default
    
    def __init__(self):
        """Initialize context manager"""
        self.messages = []
    
    # ========== Add Messages ==========
    
    def add_user_message(self, text: str, mode: str):
        self.messages.append({
            "role": "user",
            "content": text,
            "mode": mode
        })
    
    def add_sql_result(self, code: str, result_df: pd.DataFrame):
        """
        Add SQL execution result to context (compact format).
        
        Args:
            code: SQL query that was executed
            result_df: Result DataFrame
        """
        # Format result compactly
        result_context = self._format_dataframe_compact(result_df)
        
        ai_message = f"""Executed SQL:
                    ```sql
                    {code}
                    ```
                    {result_context}
                    """
        
        self.messages.append({
            "role": "assistant",
            "content": ai_message,
            "mode": "sql"
        })

    def add_python_result(self, code: str, result: dict):
        """
        Add Python execution result to context (compact format).
        
        Args:
            code: Python code that was executed
            result: Execution result dict (output, fig, namespace)
        """
        # Format result compactly
        result_context = self._format_python_compact(result)
        
        ai_message = f"""Executed Python:
                    ```python
                    {code}
                    ```
                    {result_context}
                    """
        
        self.messages.append({
            "role": "assistant",
            "content": ai_message,
            "mode": "python"
        })
    
    def add_error(self, code: str, error: str, mode: str):
        """
        Add error to context.
        
        Args:
            code: Code that failed
            error: Error message
            mode: Mode (sql/python)
        """
        self.messages.append({
            "role": "assistant",
            "content": f"{mode.upper()}:\n{code}\n\nError: {error}",
            "mode": mode
        })
    
    # ========== Get Context ==========
    
    def get_context_for_ai(self, limit: int = DEFAULT_CONTEXT_LIMIT) -> list:
        """
        Get conversation context for AI (last N messages).
        """
        return self.messages[-limit:] if len(self.messages) > 0 else []
    
    # ========== Formatting Utilities (Private) ==========
    
    def _format_dataframe_compact(self, df: pd.DataFrame) -> str:
        """
        Format DataFrame into compact text (~200 tokens max).
        
        Strategy:
        - Show row/column counts
        - List column names
        - Show 1-2 sample rows (key values only)
        - Identify patterns if possible
        - Max 800 chars (~200 tokens)
        
        Args:
            df: DataFrame to format
        
        Returns:
            str: Compact representation
        """
        if df.empty:
            return "Empty result (0 rows)"
        
        # Basic stats
        parts = [f"Results: {len(df)} rows × {len(df.columns)} columns"]
        
        # Column names
        col_names = ", ".join(df.columns[:10])
        if len(df.columns) > 10:
            col_names += f", ... ({len(df.columns) - 10} more)"
        parts.append(f"Columns: {col_names}")
        
        # Identify patterns (common values in first few columns)
        patterns = []
        for col in df.columns[:3]:
            unique_count = df[col].nunique()
            if unique_count == 1:
                patterns.append(f"All {col}={df[col].iloc[0]}")
            elif unique_count <= 3:
                values = df[col].unique()[:3]
                patterns.append(f"{col} values: {', '.join(map(str, values))}")
        
        if patterns:
            parts.append("Patterns: " + "; ".join(patterns))
        
        # Sample rows (compact format)
        sample_size = min(2, len(df))
        sample_rows = []
        for idx in range(sample_size):
            row = df.iloc[idx]
            # Show first 3-4 key columns only
            row_parts = []
            for col in df.columns[:4]:
                val = row[col]
                # Truncate long strings
                if isinstance(val, str) and len(val) > 20:
                    val = val[:20] + "..."
                row_parts.append(f"{col}={val}")
            sample_rows.append(", ".join(row_parts))
        
        if sample_rows:
            parts.append("Sample: " + " | ".join(sample_rows))
        
        # Join and truncate to max length
        result = "\n".join(parts)
        
        if len(result) > self.MAX_MESSAGE_LENGTH:
            result = result[:self.MAX_MESSAGE_LENGTH] + "..."
        
        return result
    
    def _format_python_compact(self, result: dict) -> str:
        """
        Format Python execution result compactly (~200 tokens max).
        
        Args:
            result: Dict with 'output', 'fig', 'namespace'
        
        Returns:
            str: Compact representation
        """
        parts = []
        
        # Console output (truncated)
        if result.get('output'):
            output = result['output']
            lines = output.split('\n')[:5]  # First 5 lines only
            truncated = '\n'.join(lines)
            if len(lines) < len(output.split('\n')):
                truncated += "\n... (truncated)"
            parts.append(f"Output:\n{truncated}")
        
        # Chart
        if result.get('fig'):
            parts.append("Generated chart (Plotly figure)")
        
        # DataFrames created
        for var_name, var_value in result.get('namespace', {}).items():
            if isinstance(var_value, pd.DataFrame):
                parts.append(f"Created DataFrame '{var_name}': {len(var_value)} rows × {len(var_value.columns)} columns")
        
        if not parts:
            return "Code executed successfully (no output)"
        
        result_text = "\n".join(parts)
        
        # Truncate if too long
        if len(result_text) > self.MAX_MESSAGE_LENGTH:
            result_text = result_text[:self.MAX_MESSAGE_LENGTH] + "..."
        
        return result_text
    
    # ========== Management ==========
    
    def clear(self):
        """Clear all conversation history"""
        self.messages = []
    
    def get_message_count(self) -> int:
        """Get total number of messages"""
        return len(self.messages)
    
    def estimate_tokens(self) -> int:
        """
        Estimate total tokens in current context.
        Rough estimate: ~4 chars = 1 token
        
        Returns:
            int: Estimated token count
        """
        total_chars = sum(len(msg['content']) for msg in self.messages)
        return total_chars // 4