"""
Code execution engine for SQL and Python
"""
import pandas as pd
import duckdb
import io
import sys
import plotly.express as px
import plotly.graph_objects as go


class CodeExecutor:
    """Executes SQL and Python code safely"""
    
    def execute_sql(
            self, 
            conn: duckdb.DuckDBPyConnection, 
            df: pd.DataFrame, 
            code: str) -> tuple:
        """
        Execute SQL query (SELECT only).
        
        Args:
            conn: DuckDB connection
            df: DataFrame to query
            code: SQL query string
        
        Returns:
            tuple: (result_df, error)
                - result_df: Result DataFrame if successful, None if error
                - error: Error message if failed, None if successful
        """
        # Security: Only allow SELECT queries
        code_upper = code.strip().upper()
        
        if not code_upper.startswith('SELECT'):
            return None, "Only SELECT queries are allowed in SQL mode"
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
            'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in code_upper:
                return None, f"Dangerous keyword '{keyword}' is not allowed"
        
        # Execute query
        try:
            conn.register('df', df)
            result = conn.execute(code).df()
            return result, None
        except Exception as e:
            return None, str(e)
    
    def execute_python(self, conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, code: str) -> tuple:
        """
        Execute Python code with restricted namespace.
        
        ⚠️ WARNING: Executes arbitrary Python code!
        - For internal/trusted use only
        - Basic restrictions prevent accidents, not determined attacks
        - DO NOT expose to untrusted users
        
        Args:
            conn: DuckDB connection
            df: DataFrame to work with
            code: Python code string
        
        Returns:
            tuple: (result, error)
                - result: Dict with 'output', 'fig', 'namespace' if successful
                - error: Error message if failed
        """
        # Basic blacklist (prevents accidents, not attacks)
        forbidden_patterns = [
            'os.system', 'subprocess', 'eval(', 'exec(',
            '__import__', 'compile', 'open('
        ]
        
        code_lower = code.lower()
        for pattern in forbidden_patterns:
            if pattern in code_lower:
                return None, f"Forbidden operation: '{pattern}' is not allowed for safety"
        
        try:
            # Restricted namespace (reduces accident risk)
            namespace = {
                'df': df,
                'conn': conn,
                'pd': pd,
                'px': px,
                'go': go,
                # Provide minimal safe builtins
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'zip': zip,
                    'print': print,
                    'type': type,
                    'isinstance': isinstance,
                    # NO: __import__, eval, exec, open, input, compile
                }
            }
            
            # Capture stdout
            output_buffer = io.StringIO()
            sys.stdout = output_buffer
            
            # Execute code
            exec(code, namespace)
            
            # Restore stdout
            sys.stdout = sys.__stdout__
            output = output_buffer.getvalue()
            
            # Extract figure if created
            fig = namespace.get('fig')
            
            # Extract any DataFrames created (excluding 'df' and 'conn')
            user_namespace = {
                k: v for k, v in namespace.items()
                if k not in ['df', 'conn', 'pd', 'px', 'go', '__builtins__']
                   and not k.startswith('_')
            }
            
            result = {
                'output': output,
                'fig': fig,
                'namespace': user_namespace
            }
            
            return result, None
            
        except Exception as e:
            # Restore stdout on error
            sys.stdout = sys.__stdout__
            return None, str(e)