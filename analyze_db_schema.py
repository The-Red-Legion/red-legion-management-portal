#!/usr/bin/env python3
"""
Database Schema Analysis Script
Connects to the Red Legion database and examines tables related to Discord users, guilds, and roles.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use main database URL
DATABASE_URL = os.getenv("DATABASE_URL")

async def analyze_database_schema():
    """Connect to database and analyze schema for Discord-related tables."""
    try:
        # Connect to database
        print("Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✓ Connected successfully!")
        
        # Get all tables in the database
        print("\n=== ALL TABLES IN DATABASE ===")
        tables_query = """
        SELECT table_name, table_schema
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        
        tables = await conn.fetch(tables_query)
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # Look for Discord-related tables specifically
        discord_related_tables = []
        for table in tables:
            table_name = table['table_name'].lower()
            if any(keyword in table_name for keyword in ['user', 'guild', 'role', 'member', 'discord']):
                discord_related_tables.append(table['table_name'])
        
        print(f"\n=== DISCORD-RELATED TABLES ({len(discord_related_tables)}) ===")
        for table in discord_related_tables:
            print(f"  - {table}")
        
        # Examine schema of each Discord-related table
        for table_name in discord_related_tables:
            print(f"\n=== SCHEMA FOR TABLE: {table_name} ===")
            
            # Get column information
            columns_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = $1 AND table_schema = 'public'
            ORDER BY ordinal_position;
            """
            
            columns = await conn.fetch(columns_query, table_name)
            print("Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            # Get foreign key constraints
            fk_query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = $1;
            """
            
            foreign_keys = await conn.fetch(fk_query, table_name)
            if foreign_keys:
                print("Foreign Keys:")
                for fk in foreign_keys:
                    print(f"  - {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
            
            # Get sample data (first 5 rows)
            try:
                sample_query = f'SELECT * FROM "{table_name}" LIMIT 5'
                sample_data = await conn.fetch(sample_query)
                print(f"Sample data ({len(sample_data)} rows):")
                if sample_data:
                    # Print column headers
                    headers = list(sample_data[0].keys())
                    print(f"  {' | '.join(headers)}")
                    print(f"  {'-' * (len(' | '.join(headers)))}")
                    
                    # Print data rows
                    for row in sample_data:
                        values = []
                        for value in row.values():
                            str_val = str(value) if value is not None else "NULL"
                            # Truncate long values
                            if len(str_val) > 30:
                                str_val = str_val[:27] + "..."
                            values.append(str_val)
                        print(f"  {' | '.join(values)}")
                else:
                    print("  (No data)")
            except Exception as e:
                print(f"  Error fetching sample data: {e}")
                
            print()
        
        # Look for any tables that might contain guild membership or role data
        print("=== SEARCHING FOR ROLE/MEMBERSHIP DATA ===")
        
        # Check if there are tables with role or permission data
        for table in tables:
            table_name = table['table_name']
            try:
                # Look for columns that might contain Discord IDs or role information
                columns_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = $1 AND table_schema = 'public'
                AND (column_name ILIKE '%discord%' OR 
                     column_name ILIKE '%role%' OR 
                     column_name ILIKE '%guild%' OR
                     column_name ILIKE '%member%' OR
                     column_name ILIKE '%user_id%')
                ORDER BY ordinal_position;
                """
                
                relevant_columns = await conn.fetch(columns_query, table_name)
                if relevant_columns:
                    print(f"\nTable '{table_name}' has relevant columns:")
                    for col in relevant_columns:
                        print(f"  - {col['column_name']}: {col['data_type']}")
                    
                    # Get a few sample values for these columns
                    column_names = [col['column_name'] for col in relevant_columns]
                    sample_query = f'SELECT {", ".join(column_names)} FROM "{table_name}" LIMIT 3'
                    try:
                        sample_data = await conn.fetch(sample_query)
                        if sample_data:
                            print("  Sample values:")
                            for row in sample_data:
                                values = [str(val) if val is not None else "NULL" for val in row.values()]
                                print(f"    {dict(zip(column_names, values))}")
                    except Exception as e:
                        print(f"    Error fetching sample: {e}")
                        
            except Exception as e:
                continue
        
        await conn.close()
        print("\n✓ Analysis complete!")
        
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        print(f"Database URL: {DATABASE_URL}")

if __name__ == "__main__":
    asyncio.run(analyze_database_schema())