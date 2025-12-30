import pandas as pd

def build_natural_language_prompt(metadata: dict) -> str:
    """
    Build system prompt for natural language conversational mode.

    Args:
        metadata: Data source metadata dict

    Returns:
        str: System prompt
    """
    description = metadata.get('description', 'this dataset')
    key_columns = metadata.get('key_columns', '')
    notes = metadata.get('notes', '')

    return f"""You are a helpful assistant for analyzing {description}.
            Key information about the data:
            {key_columns}
            {notes}
            Be concise and helpful."""

def build_sql_prompt(df: pd.DataFrame, metadata: dict) -> str:
    """
    Build system prompt for SQL query generation.

    Args:
        df: DataFrame to query
        metadata: Data source metadata dict

    Returns:
        str: System prompt
    """
    # Get schema info (truncated to save tokens)
    columns = ", ".join(df.columns[:15])
    if len(df.columns) > 15:
        columns += f", ... ({len(df.columns) - 15} more)"

    # Get sample data (compact)
    sample = df.head(2).to_string(max_colwidth=20, index=False)

    return f"""You are a SQL query generator for DuckDB. Generate ONLY valid SQL queries.
            DataFrame '{metadata['table_name']}':
            Columns: {columns}
            Row count: {len(df):,}
            Sample data (first 2 rows):
            {sample}
            Domain rules:
            {metadata.get('domain_rules', '')}
            CRITICAL RULES:
            - Return ONLY a valid SQL query
            - Query from: df
            - Use DuckDB SQL syntax
            - NO explanations, NO comments, NO markdown
            - Just the SQL query itself
            """

def build_python_prompt(df: pd.DataFrame, metadata: dict) -> str:
      """
      Build system prompt for Python code generation.

      Args:
          df: DataFrame to analyze
          metadata: Data source metadata dict

      Returns:
          str: System prompt
      """
      columns = ", ".join(df.columns[:15])
      if len(df.columns) > 15:
          columns += f", ... ({len(df.columns) - 15} more)"

      sample = df.head(2).to_string(max_colwidth=20, index=False)

      return f"""You are a Python code generator for data analysis and visualization.

            DataFrame '{metadata['table_name']}':
            Columns: {columns}
            Row count: {len(df):,}

            Sample data:
            {sample}

            Available tools:
            - df: pandas DataFrame with the data
            - conn: DuckDB connection
            - pd: pandas
            - px: plotly.express (for charts)
            - go: plotly.graph_objects (for advanced charts)

            Domain context: {metadata.get('description', '')}

            CRITICAL RULES FOR VISUALIZATIONS:
            1. For Plotly charts: Create figure and assign to variable 'fig'
            2. NEVER use fig.show() - this will cause errors
            3. Example: fig = px.bar(df, x='col1', y='col2')
            4. For multiple plots: Create separate figs (fig1, fig2, etc)

            CRITICAL RULES FOR CODE:
            - Return ONLY Python code
            - NO explanations, NO markdown, NO comments
            - Just the code itself
            - Use print() to show results
            - Don't use display() or show()
            """


def build_error_retry_prompt(
      df: pd.DataFrame,
      user_query: str,
      failed_code: str,
      error: str,
      mode: str,
      metadata: dict
    ) -> str:
      """
      Build retry prompt when generated code failed.

      Args:
          df: DataFrame being queried
          user_query: User's original question
          failed_code: Code that failed
          error: Error message
          mode: "sql" or "python"
          metadata: Data source metadata dict

      Returns:
          str: System prompt for retry
      """
      lang = "SQL" if mode == "sql" else "Python"

      columns = ", ".join(df.columns[:10])

      return f"""You are a {lang} code generator. Your previous code failed with an error.

                DataFrame columns: {columns}

                User's original question: {user_query}

                Your previous code:
                {failed_code}

                Error message:
                {error}

                Generate CORRECTED {lang} code that fixes this error.
                Return ONLY the corrected code, no explanations.
                """