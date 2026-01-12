import psycopg2
import sys

# Connection parameters from settings.py
DB_NAME = 'qawaq_db'
DB_USER = 'qawaq_man'
DB_PASS = 'Q@w4Q'
DB_HOST = 'localhost'
DB_PORT = '5432'

print(f"Testing connection to {DB_NAME} as {DB_USER}...")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    print("SUCCESS: Connection established!")
    conn.close()
except Exception as e:
    print("\nCONNECTION FAILED")
    
    # Try to decode the error message safely
    try:
        # Default string conversion might fail if default encoding is utf-8 and error is cp1252
        print(f"Error (Standard): {e}")
    except:
        pass
        
    # Access the error message bytes directly if possible or force decoding
    try:
        # psycopg2 errors usually have a 'diag' attribute or we can convert the exception object to bytes
        error_str = str(e) # This might have failed above
    except UnicodeDecodeError:
        # If str(e) fails, the exception contains bytes that don't match default encoding
        # We can try to assume it's Latin-1 or CP1252 (common in Windows Spanish)
        try:
            # We can't easily get the raw bytes from the exception object standardly in python 3 if str() fails 
            # effectively, but for psycopg2 we can try accessing pgcode or similar.
            pass
        except:
            pass
            
    # Attempt manual print with replace
    try:
        # In Python 3, str(e) tries to decode. If it fails, we are in a bind.
        # But we can try to print the args.
        print(f"Error Args: {e.args}")
        for arg in e.args:
            if isinstance(arg, str):
                print(f"Arg (str): {arg}")
            elif isinstance(arg, bytes):
                print(f"Arg (decoded replace): {arg.decode('cp1252', errors='replace')}")
    except Exception as inner:
        print(f"Could not print error details: {inner}")

print("\nSuggestions:")
print("1. Check if user 'qawaq_man' exists.")
print("2. Check if database 'qawaq_db' exists.")
print("3. Check if password 'Q@w4Q' is correct.")
