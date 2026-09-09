import streamlit as st
import duckdb

# Configure page settings for compact, technical layout
st.set_page_config(
    page_title="In-Sight Entity Resolution",
    layout="wide"
)

# Initialize cached DuckDB connection and remote Parquet view
@st.cache_resource
def get_duckdb_client():
    con = duckdb.connect(database=":memory:", read_only=False)
    
    # Configure network resilience for remote Hugging Face fetches
    con.execute("SET http_timeout = '120s';")
    con.execute("SET http_retries = 5;")
    con.execute("SET http_retry_backoff = 2.0;")
    
    # Load required network extension
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    # Create a remote view to prevent full-table decompression into RAM
    con.execute("""
        CREATE VIEW nc_data AS 
        SELECT * FROM read_parquet('hf://datasets/jacobmgreer/in-sight/**/*.parquet');
    """)
    
    return con

con = get_duckdb_client()

st.title("In-Sight Graph Exploration Engine")

# Sidebar controls for filtering entity pairs
st.sidebar.header("Filter Parameters")

selected_type = st.sidebar.selectbox(
    "Entity Type",
    options=[1, 2, 3], # Adjust based on your schema identifiers
    format_func=lambda x: f"Type {x}"
)

selected_decade = st.sidebar.selectbox(
    "Decade Filter",
    options=[None, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020],
    format_func=lambda x: "All Decades" if x is None else f"{x}s"
)

# Construct parameterized query using bitwise operations for decade fingerprints
query_base = """
    SELECT big, type, comp
    FROM nc_data
    WHERE type = ?
"""

params = [selected_type]

if selected_decade is not None:
    # Evaluates bitwise containment against the decade bitmask column
    query_base += " AND ((COALESCE(decades, 0)::BIGINT & (1::BIGINT << ?)) <> 0)"
    params.append(selected_decade)

query_base += " LIMIT 1000;"

# Execute query and stream results into a dataframe
@st.cache_data
def run_query(query, parameters):
    return con.execute(query, parameters).df()

df_results = run_query(query_base, params)

# Display execution summary metrics
col1, col2 = st.columns(2)
col1.metric("Returned Rows", len(df_results))
col2.metric("Execution Engine", "DuckDB-Wasm / In-Memory Python Backend")

# Render data table
st.subheader("Candidate Pairs & Edge Decisions")
st.dataframe(df_results, use_container_width=True)