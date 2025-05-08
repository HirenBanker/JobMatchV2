import psycopg2
from psycopg2.extras import DictCursor # For easier row access
from app.database.connection import get_connection
import streamlit as st
from decimal import Decimal

class CreditPackage:
    def __init__(self, id=None, name=None, description=None, credits_amount=None,
                 price_inr=None, is_active=True, sort_order=0,
                 created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.credits_amount = credits_amount
        self.price_inr = Decimal(price_inr) if price_inr is not None else None # Ensure price is Decimal
        self.is_active = is_active
        self.sort_order = sort_order
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    @st.cache_data(ttl=3600) # Cache for 1 hour
    def get_all_active_sorted():
        """Fetches all active credit packages, sorted by sort_order."""
        conn = get_connection()
        if conn is None:
            return []
        
        packages = []
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT * FROM credit_packages
                WHERE is_active = TRUE
                ORDER BY sort_order ASC, name ASC
            """)
            for row in cursor.fetchall():
                packages.append(CreditPackage(**row))
        except psycopg2.Error as e:
            print(f"Error fetching active credit packages: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()
        return packages

    @staticmethod
    def get_all(include_inactive=False):
        """Fetches all credit packages, optionally including inactive ones, sorted by sort_order."""
        conn = get_connection()
        if conn is None:
            return []
        
        packages = []
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            sql = "SELECT * FROM credit_packages ORDER BY sort_order ASC, name ASC"
            if not include_inactive:
                sql = "SELECT * FROM credit_packages WHERE is_active = TRUE ORDER BY sort_order ASC, name ASC"
            
            cursor.execute(sql)
            for row in cursor.fetchall():
                packages.append(CreditPackage(**row))
        except psycopg2.Error as e:
            print(f"Error fetching credit packages: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()
        return packages

    @staticmethod
    def get_by_id(package_id):
        conn = get_connection()
        if conn is None:
            return None
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM credit_packages WHERE id = %s", (package_id,))
            row = cursor.fetchone()
            if row:
                return CreditPackage(**row)
            return None
        except psycopg2.Error as e:
            print(f"Error fetching package by ID: {e}")
            return None
        finally:
            if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def create(name, description, credits_amount, price_inr, is_active=True, sort_order=0):
        conn = get_connection()
        if conn is None:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credit_packages (name, description, credits_amount, price_inr, is_active, sort_order, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (name, description, int(credits_amount), Decimal(price_inr), bool(is_active), int(sort_order)))
            package_id = cursor.fetchone()[0]
            conn.commit()
            CreditPackage.clear_all_caches() # Clear cache
            return package_id
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error creating credit package: {e}")
            return None
        finally:
            if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def update(package_id, name, description, credits_amount, price_inr, is_active, sort_order):
        conn = get_connection()
        if conn is None:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE credit_packages
                SET name = %s, description = %s, credits_amount = %s, price_inr = %s,
                    is_active = %s, sort_order = %s, updated_at = NOW()
                WHERE id = %s
            """, (name, description, int(credits_amount), Decimal(price_inr), bool(is_active), int(sort_order), package_id))
            conn.commit()
            CreditPackage.clear_all_caches() # Clear cache
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating credit package: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def delete(package_id):
        conn = get_connection()
        if conn is None:
            return False
        try:
            cursor = conn.cursor()
            # Before deleting, you might want to check if this package is part of any transactions
            # or simply disallow deletion and only allow deactivation.
            # For now, direct delete:
            cursor.execute("DELETE FROM credit_packages WHERE id = %s", (package_id,))
            conn.commit()
            CreditPackage.clear_all_caches() # Clear cache
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error deleting credit package: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def clear_all_caches():
        """Clears all Streamlit cache_data associated with this class."""
        CreditPackage.get_all_active_sorted.clear()
        # If you add more @st.cache_data methods, clear them here too.
        print("CreditPackage caches cleared.")

    def __repr__(self):
        return (f"<CreditPackage(id={self.id}, name='{self.name}', credits={self.credits_amount}, "
                f"price_inr={self.price_inr}, active={self.is_active})>")