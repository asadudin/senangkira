#!/usr/bin/env python
"""
Script to deploy the existing schema.sql to PostgreSQL database.
This handles the initial database setup before Django migrations.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def deploy_schema():
    """Deploy schema.sql to the PostgreSQL database."""
    
    # Database connection string from env.md
    DATABASE_URL = "postgresql://padux:passwordrahsia@192.168.31.117:5432/senangkira?schema=public"
    
    # Parse the database URL
    db_url = urlparse(DATABASE_URL)
    
    # Connection parameters
    conn_params = {
        'host': db_url.hostname,
        'port': db_url.port,
        'database': 'senangkira',
        'user': db_url.username,
        'password': db_url.password
    }
    
    try:
        # Connect directly to senangkira database
        print("Connecting to senangkira database...")
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'docs', 'schema.sql')
        print(f"Reading schema from: {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print("Executing schema.sql...")
        cursor.execute(schema_sql)
        conn.commit()
        
        # Verify some key tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Test UUID generation
        cursor.execute("SELECT gen_random_uuid()")
        uuid_test = cursor.fetchone()[0]
        print(f"\nUUID generation test: {uuid_test}")
        
        print("\n✅ Schema deployment completed successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ schema.sql file not found in docs/ directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    deploy_schema()