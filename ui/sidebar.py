"""
Sidebar components for data source info, query library, and cost tracker
"""
import streamlit as st
from core.query_library import QueryLibrary
from config import get_active_metadata


def render_sidebar(state, data_source, query_library: QueryLibrary):
    """
    Render complete sidebar with all components.
    
    Args:
        state: AppState instance
        data_source: DataSourceManager instance
        query_library: QueryLibrary instance
    """
    with st.sidebar:
        # Data source info
        render_data_source_info(state, data_source)
        st.divider()
        
        # Query library
        render_query_library(query_library, state)
        st.divider()
        
        # Cost tracker
        render_cost_tracker(state)


def render_data_source_info(state, data_source):
    """
    Display current data source information.
    
    Args:
        state: AppState instance
        data_source: DataSourceManager instance
    """
    st.subheader("📊 Data Source")
    
    meta = get_active_metadata()
    
    # Get icon
    icon = meta.get('icon', '📊')
    
    # Display name with icon
    st.info(f"**{icon} {meta['display_name']}**")
    
    # Table info
    st.caption(f"📋 Table: `{meta['name']}`")
    
    # Schema info
    if state.is_data_loaded():
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Rows", f"{len(state.df):,}")
        with col2:
            st.metric("Columns", len(state.df.columns))
    else:
        st.caption("⏳ Data not loaded")


def render_query_library(query_library: QueryLibrary, state):
    """
    Display query library browser.
    
    Args:
        query_library: QueryLibrary instance
        state: AppState instance
    """
    st.subheader("📚 Query Library")
    
    # Filter
    mode_filter = st.selectbox(
        "Filter by mode",
        ["All", "SQL", "Python"],
        key="query_filter"
    )
    
    # Get queries
    filter_mode = None if mode_filter == "All" else mode_filter.lower()
    queries = query_library.list(filter_mode=filter_mode)
    
    if not queries:
        st.caption("No saved queries yet")
        st.info("💡 **How to save:**\n\n1. Execute a query\n2. Click **💾 Save Query** below the result\n3. It will appear here!")
        return
    
    # Display count
    st.caption(f"**{len(queries)} saved {mode_filter.lower() if mode_filter != 'All' else ''} queries**")
    
    # Display queries
    for query in queries:
        render_query_card(query, query_library, state)


def render_query_card(query: dict, query_library: QueryLibrary, state):
    """
    Render a single query card.
    
    Args:
        query: Query dict
        query_library: QueryLibrary instance
        state: AppState instance
    """
    with st.container():
        # Header with name and actions
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Query name (clickable to load)
            truncated_name = query['name'][:35] + "..." if len(query['name']) > 35 else query['name']
            if st.button(
                f"▶️ {truncated_name}",
                key=f"load_{query['id']}",
                use_container_width=True,
                help="Click to load and execute this query"
            ):
                # Set load trigger
                st.session_state.load_query_id = query['id']
                st.rerun()
        
        with col2:
            # Delete button
            if st.button("🗑️", key=f"del_{query['id']}", help="Delete query"):
                if st.session_state.get(f"confirm_delete_{query['id']}"):
                    query_library.delete(query['id'])
                    st.session_state[f"confirm_delete_{query['id']}"] = False
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{query['id']}"] = True
                    st.warning("Click again to confirm delete")
                    st.rerun()
        
        # Mode badge and stats
        mode_emoji = "📊" if query['mode'] == "sql" else "🐍"
        mode_label = query['mode'].upper()
        
        col_mode, col_stats = st.columns([1, 3])
        with col_mode:
            st.caption(f"{mode_emoji} **{mode_label}**")
        with col_stats:
            st.caption(f"Used {query.get('use_count', 0)}x • {query.get('created_at', '')[:10]}")
        
        # Description (if exists)
        if query.get('description') and query['description'].strip():
            desc = query['description']
            truncated_desc = desc[:60] + "..." if len(desc) > 60 else desc
            st.caption(f"💬 _{truncated_desc}_")
        
        st.markdown("---")


def render_cost_tracker(state):
    """
    Display API cost tracking information.
    
    Args:
        state: AppState instance
    """
    st.subheader("💰 Cost Tracker")
    
    # Total cost and calls
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total", f"${state.total_cost:.4f}")
    with col2:
        st.metric("Calls", state.api_calls)
    
    # Show details in expander
    if state.cost_history:
        with st.expander("📊 Call History", expanded=False):
            st.caption("**Recent API Calls:**")
            
            # Show last 10 calls
            for idx, call in enumerate(reversed(state.cost_history[-10:])):
                st.caption(
                    f"{idx+1}. {call.get('model', 'unknown')} • "
                    f"${call.get('cost', 0):.5f} • "
                    f"{call.get('mode', 'N/A').upper()}"
                )
            
            if len(state.cost_history) > 10:
                st.caption(f"... and {len(state.cost_history) - 10} more")
            
            st.divider()
            
            # Clear button
            if st.button("🗑️ Reset Tracker", key="clear_cost_history", use_container_width=True):
                state.cost_history = []
                state.total_cost = 0.0
                state.api_calls = 0
                st.success("✅ Cost tracker reset")
                st.rerun()
    else:
        st.caption("No API calls yet")