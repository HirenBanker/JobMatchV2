import streamlit as st
from app.database.connection import get_connection
import psycopg2 # Import psycopg2 for specific error handling if needed

@st.cache_data(ttl=300) # Cache for 5 minutes
def get_platform_setting(key: str, default_value: any = None) -> any:
    """
    Retrieves a specific setting from the platform_settings table.
    Caches the result to minimize database queries.
    """
    conn = get_connection()
    if conn is None:
        # st.warning(f"Database connection failed. Using default value for setting '{key}'.")
        print(f"Database connection failed for get_platform_setting. Using default for '{key}'.")
        return default_value
    
    cursor = None  # Initialize cursor to None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM platform_settings WHERE key = %s", (key,))
        result = cursor.fetchone()
        return result[0] if result else default_value
    except (Exception, psycopg2.Error) as e: # Catch generic and psycopg2 errors
        # st.error(f"Error fetching platform setting '{key}': {e}")
        print(f"Error fetching platform setting '{key}': {e}")
        return default_value
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()