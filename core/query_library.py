"""
Query library management using JSON file storage

Stores saved queries in data/queries.json for easy access and reuse.

Future migration path to database:
- Replace _load_queries() and _save_queries() methods
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class QueryLibrary:
    """Manages saved queries using JSON file storage"""
    
    # Storage location
    DATA_DIR = Path("data")
    QUERIES_FILE = DATA_DIR / "queries.json"
    
    def __init__(self):
        """Initialize query library and ensure data directory exists"""
        self.DATA_DIR.mkdir(exist_ok=True)
        
        # Create queries file if it doesn't exist
        if not self.QUERIES_FILE.exists():
            self._save_queries([])
    
    # ========== Public Methods ==========
    
    def save(self, name: str, code: str, mode: str, description: str = "") -> str:
        """
        Save a new query.
        
        Args:
            name: Query name
            code: SQL or Python code
            mode: "sql" or "python"
            description: Optional description
        
        Returns:
            str: Query ID (UUID)
        """
        queries = self._load_queries()
        
        query_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        query = {
            "id": query_id,
            "name": name,
            "description": description,
            "mode": mode,
            "code": code,
            "tags": [],
            "created_at": now,
            "last_used": now,
            "use_count": 0
        }
        
        queries.append(query)
        self._save_queries(queries)
        
        return query_id
    
    def load(self, query_id: str) -> Optional[Dict]:
        """
        Load a query by ID and update usage stats.
        
        Args:
            query_id: Query ID to load
        
        Returns:
            dict: Query data or None if not found
        """
        queries = self._load_queries()
        
        for query in queries:
            if query["id"] == query_id:
                # Update usage stats
                query["last_used"] = datetime.now().isoformat()
                query["use_count"] = query.get("use_count", 0) + 1
                self._save_queries(queries)
                return query
        
        return None
    
    def list(self, filter_mode: Optional[str] = None) -> List[Dict]:
        """
        List all queries, optionally filtered by mode.
        
        Args:
            filter_mode: Optional mode filter ("sql" or "python")
        
        Returns:
            list: List of query dicts, sorted by last_used (most recent first)
        """
        queries = self._load_queries()
        
        # Filter by mode if specified
        if filter_mode:
            queries = [q for q in queries if q["mode"] == filter_mode]
        
        # Sort by last_used (most recent first)
        queries.sort(key=lambda q: q.get("last_used", ""), reverse=True)
        
        return queries
    
    def delete(self, query_id: str) -> bool:
        """
        Delete a query by ID.
        
        Args:
            query_id: Query ID to delete
        
        Returns:
            bool: True if deleted, False if not found
        """
        queries = self._load_queries()
        initial_length = len(queries)
        
        # Filter out the query to delete
        queries = [q for q in queries if q["id"] != query_id]
        
        if len(queries) < initial_length:
            self._save_queries(queries)
            return True
        
        return False
    
    def search(self, keyword: str) -> List[Dict]:
        """
        Search queries by keyword in name or description.
        
        Args:
            keyword: Keyword to search for
        
        Returns:
            list: Matching queries
        """
        queries = self._load_queries()
        keyword_lower = keyword.lower()
        
        matches = [
            q for q in queries
            if keyword_lower in q["name"].lower()
            or keyword_lower in q.get("description", "").lower()
        ]
        
        return matches
    
    # ========== Private Methods ==========
    
    def _load_queries(self) -> List[Dict]:
        """
        Load queries from JSON file.
        
        To migrate to database: Replace this method to query DB instead.
        
        Returns:
            list: List of query dicts
        """
        try:
            with open(self.QUERIES_FILE, 'r') as f:
                data = json.load(f)
                return data.get("queries", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_queries(self, queries: List[Dict]):
        """
        Save queries to JSON file.
        
        To migrate to database: Replace this method to write to DB instead.
        
        Args:
            queries: List of query dicts to save
        """
        with open(self.QUERIES_FILE, 'w') as f:
            json.dump({"queries": queries}, f, indent=2)
    
    # ========== Utility Methods ==========
    
    def get_query_count(self) -> int:
        """Get total number of saved queries"""
        return len(self._load_queries())
    
    def clear_all(self):
        """Delete all queries (use with caution!)"""
        self._save_queries([])
