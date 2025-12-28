"""
AI service for code generation via OpenAI API

Handles:
- Prompt construction with DataFrame context
- Model selection based on query complexity
- OpenAI API calls
- Response cleaning and validation
- Cost calculation and metadata tracking
"""
from openai import OpenAI
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Iterator, Tuple
from config import (
    OPENAI_API_KEY,
    MODEL_CHEAP,
    MODEL_MEDIUM,
    MODEL_SMART,
    MODEL_PRICING,
    get_active_metadata
)


@dataclass
class GenerationMetadata:
    """Metadata about code generation"""
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    source: str  # "generated" or "direct"


class AIService:
    """AI service for generating SQL, Python, and conversational text"""
    
    def __init__(self):
        """Initialize AI service with OpenAI client"""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    # ========== Public Methods ==========
    
    def generate_sql(
        self,
        user_query: str,
        df: pd.DataFrame,
        context: list,
        error_context: Optional[dict] = None
    ) -> Tuple[str, GenerationMetadata]:
        """
        Generate SQL query from natural language.
        
        Args:
            user_query: User's question in natural language
            df: DataFrame to query (for schema info)
            context: Conversation context from ContextManager
            error_context: Optional dict with failed_query and error for retry
        
        Returns:
            tuple: (sql_code, metadata)
        """
        # Select model
        model = self._select_model(user_query)
        
        # Build prompt
        if error_context:
            system_prompt = self._build_error_retry_prompt(
                df,
                user_query,
                error_context['failed_query'],
                error_context['error'],
                mode="sql"
            )
        else:
            system_prompt = self._build_sql_prompt(df)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_query})
        
        # Call API
        response, usage = self._call_api(messages, model, stream=False)
        
        # Extract and clean code
        raw_code = response.choices[0].message.content.strip()
        code = self._clean_code(raw_code, "sql")
        
        # Calculate cost and create metadata
        cost = self._calculate_cost(model, usage['input_tokens'], usage['output_tokens'])
        metadata = GenerationMetadata(
            model=model,
            input_tokens=usage['input_tokens'],
            output_tokens=usage['output_tokens'],
            cost=cost,
            source="generated"
        )
        
        return code, metadata
    
    def generate_python(
        self,
        user_query: str,
        df: pd.DataFrame,
        context: list,
        error_context: Optional[dict] = None
    ) -> Tuple[str, GenerationMetadata]:
        """
        Generate Python code from natural language.
        
        Args:
            user_query: User's question in natural language
            df: DataFrame to work with (for schema info)
            context: Conversation context from ContextManager
            error_context: Optional dict with failed_query and error for retry
        
        Returns:
            tuple: (python_code, metadata)
        """
        # Select model
        model = self._select_model(user_query)
        
        # Build prompt
        if error_context:
            system_prompt = self._build_error_retry_prompt(
                df,
                user_query,
                error_context['failed_query'],
                error_context['error'],
                mode="python"
            )
        else:
            system_prompt = self._build_python_prompt(df)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_query})
        
        # Call API
        response, usage = self._call_api(messages, model, stream=False)
        
        # Extract and clean code
        raw_code = response.choices[0].message.content.strip()
        code = self._clean_code(raw_code, "python")
        
        # Calculate cost and create metadata
        cost = self._calculate_cost(model, usage['input_tokens'], usage['output_tokens'])
        metadata = GenerationMetadata(
            model=model,
            input_tokens=usage['input_tokens'],
            output_tokens=usage['output_tokens'],
            cost=cost,
            source="generated"
        )
        
        return code, metadata
    
    def generate_text(
        self,
        user_query: str,
        context: list,
        system_prompt: str
    ) -> Tuple[Iterator, GenerationMetadata]:
        """
        Generate conversational text response (streaming).
        
        Args:
            user_query: User's question
            context: Conversation context
            system_prompt: System prompt for conversational mode
        
        Returns:
            tuple: (response_stream, metadata)
        """
        # Select model
        model = self._select_model(user_query)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_query})
        
        # Call API with streaming
        response_stream, usage = self._call_api(messages, model, stream=True)
        
        # For streaming, we estimate cost (will track actual later)
        metadata = GenerationMetadata(
            model=model,
            input_tokens=0,  # Will be updated later
            output_tokens=0,
            cost=0.0,
            source="generated"
        )
        
        return response_stream, metadata
    
    # ========== Prompt Builders ==========
    
    def _build_sql_prompt(self, df: pd.DataFrame) -> str:
        """Build system prompt for SQL generation"""
        meta = get_active_metadata()
        
        # Get schema info (truncated to save tokens)
        columns = ", ".join(df.columns[:15])
        if len(df.columns) > 15:
            columns += f", ... ({len(df.columns) - 15} more)"
        
        # Get sample data (compact)
        sample = df.head(2).to_string(max_colwidth=20, index=False)
        
        return f"""You are a SQL query generator for DuckDB. Generate ONLY valid SQL queries.

                DataFrame '{meta['table_name']}':
                Columns: {columns}
                Row count: {len(df):,}

                Sample data (first 2 rows):
                {sample}

                Domain rules:
                {meta.get('domain_rules', '')}

                CRITICAL RULES:
                - Return ONLY a valid SQL query
                - Query from: df
                - Use DuckDB SQL syntax
                - NO explanations, NO comments, NO markdown
                - Just the SQL query itself

                Generate the query:"""
    
    def _build_python_prompt(self, df: pd.DataFrame) -> str:
        """Build system prompt for Python generation"""
        meta = get_active_metadata()
        
        columns = ", ".join(df.columns[:15])
        if len(df.columns) > 15:
            columns += f", ... ({len(df.columns) - 15} more)"
        
        sample = df.head(2).to_string(max_colwidth=20, index=False)
        
        return f"""You are a Python code generator for data analysis.

                DataFrame '{meta['table_name']}':
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

                Domain context: {meta.get('description', '')}

                CRITICAL RULES:
                1. Generate ONLY executable Python code
                2. For visualizations: assign figure to 'fig' variable
                3. For calculations: use print() to show results
                4. NO explanations, NO markdown, NO comments
                5. Just pure Python code

                Generate the code:"""
    
    def _build_error_retry_prompt(
        self,
        df: pd.DataFrame,
        user_query: str,
        failed_query: str,
        error: str,
        mode: str
    ) -> str:
        """Build retry prompt when code failed"""
        lang = "SQL" if mode == "sql" else "Python"
        
        columns = ", ".join(df.columns[:10])
        
        return f"""You are a {lang} code generator. Your previous code failed with an error.

                DataFrame columns: {columns}

                User's original question: {user_query}

                Your previous code:
                {failed_query}

                Error message:
                {error}

                Generate CORRECTED {lang} code that fixes this error.
                Return ONLY the corrected code, no explanations.
                """
    
    # ========== Model Selection ==========
    
    def _select_model(self, user_query: str) -> str:
        """
        Select appropriate model based on query complexity.
        
        Returns:
            str: Model name (gpt-5-nano, gpt-5-mini, or gpt-5.2)
        """
        query_lower = user_query.lower()
        
        # Smart model indicators (complex queries)
        smart_keywords = [
            'optimize', 'compare', 'analyze', 'correlation',
            'statistical', 'predict', 'forecast', 'why',
            'explain how', 'recommend', 'best approach',
            'machine learning', 'trend analysis'
        ]
        
        # Medium model indicators (moderate complexity)
        medium_keywords = [
            'group by', 'aggregate', 'summarize', 'average',
            'count by', 'top', 'bottom', 'ranking',
            'chart', 'plot', 'visualize', 'trend',
            'distribution', 'percentage'
        ]
        
        # Check for smart indicators
        if any(keyword in query_lower for keyword in smart_keywords):
            return MODEL_SMART
        
        # Check for medium indicators
        if any(keyword in query_lower for keyword in medium_keywords):
            return MODEL_MEDIUM
        
        # Long queries likely need more capability
        if len(user_query.split()) > 20:
            return MODEL_MEDIUM
        
        # Default to cheap model for simple queries
        return MODEL_CHEAP
    
    # ========== API Communication ==========
    
    def _call_api(
        self,
        messages: list,
        model: str,
        stream: bool = False
    ) -> Tuple:
        """
        Call OpenAI API.
        
        Args:
            messages: List of message dicts
            model: Model name
            stream: Whether to stream response
        
        Returns:
            tuple: (response, usage_dict)
        
        Raises:
            RuntimeError: If API call fails
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                # For streaming, return iterator and placeholder usage
                return response, {"input_tokens": 0, "output_tokens": 0}
            else:
                # For non-streaming, return complete response and usage
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
                return response, usage
        
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    # ========== Response Cleaning ==========
    
    def _clean_code(self, raw_response: str, mode: str) -> str:
        """
        Clean AI-generated code by removing markdown and explanations.
        
        Args:
            raw_response: Raw text from API
            mode: "sql" or "python"
        
        Returns:
            str: Cleaned executable code
        """
        import re
        
        # Remove markdown code blocks
        code = raw_response.replace(f"```{mode}", "")
        code = code.replace("```sql", "")
        code = code.replace("```python", "")
        code = code.replace("```", "")
        code = code.strip()
        
        # Remove explanatory lines
        lines = []
        for line in code.split('\n'):
            stripped = line.strip()
            # Skip obvious explanation lines
            if stripped and not re.match(r'^(This|The|Note|Explanation|Result|Here|Now)', stripped, re.IGNORECASE):
                lines.append(line)
            # Stop at first explanation
            elif re.match(r'^(This|The|Note|Explanation)', stripped, re.IGNORECASE):
                break
        
        code = '\n'.join(lines).strip()
        
        # For SQL: keep only first query if multiple
        if mode == "sql" and ';' in code:
            parts = code.split(';')
            code = parts[0].strip() + ';'
        
        return code
    
    # ========== Cost Calculation ==========
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API call cost.
        
        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
        
        Returns:
            float: Cost in USD
        """
        # Get pricing for model (default to cheap if unknown)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING[MODEL_CHEAP])
        
        # Pricing is per 1M tokens
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost