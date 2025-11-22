import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Your Supabase Connection Details ---
# The connection string is now read from a secure environment variable.
SUPABASE_CONN_STRING = os.environ.get('SUPABASE_CONN_STRING')

def get_db_connection():
    """Establishes a connection to the Supabase database."""
    if not SUPABASE_CONN_STRING:
        raise ValueError("SUPABASE_CONN_STRING environment variable not set.")
    conn = psycopg2.connect(SUPABASE_CONN_STRING)
    return conn

def check_card_brand(bin_str):
    """Determines the card brand from the first digit of the BIN."""
    if not bin_str:
        return 'Unknown'
    first_digit = bin_str[0]
    if first_digit == '3':
        return 'American Express'
    elif first_digit == '4':
        return 'Visa'
    elif first_digit == '5':
        return 'MasterCard'
    elif first_digit == '6':
        return 'Discover'
    else:
        return 'Unknown'

@app.route('/bina')
def bina_lookup():
    """
    Looks up BIN information in the Supabase database.
    This endpoint replicates the logic from the original bina.php file.
    """
    bin_param = request.args.get('bin', '')

    if not bin_param or not bin_param.isdigit() or len(bin_param) < 6:
        return jsonify({"error": "A valid BIN with at least 6 digits is required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Try to find a match by checking prefixes of decreasing length (6 down to 3)
        for i in range(6, 2, -1):
            prefix = bin_param[:i]
            cursor.execute("SELECT bin, country, scheme, type, brand, emoji, bank_name FROM bins WHERE bin = %s LIMIT 1", (prefix,))
            row = cursor.fetchone()

            if row:
                # We found a match
                matched_bin = {
                    "bin": row[0],
                    "country": row[1],
                    "scheme": row[2],
                    "type": row[3],
                    "brand": row[4],
                    "emoji": row[5],
                    "bank": {"name": row[6] if row[6] else 'UNKNOWN'}
                }
                cursor.close()
                return jsonify(matched_bin)

        # If no match was found, return the "UNKNOWN" response
        brand = check_card_brand(bin_param)
        unknown_bin = {
            'bin': bin_param[:6],
            'country': '',
            'scheme': brand,
            'type': '',
            'brand': brand,
            'emoji': '🏳',
            'bank': {'name': 'UNKNOWN'}
        }
        return jsonify(unknown_bin)

    except psycopg2.Error as e:
        print(f"Database error: {e}") # Log for debugging
        return jsonify({"error": "Database service unavailable"}), 503
    except ValueError as e:
        print(f"Configuration error: {e}")
        return jsonify({"error": "API not configured correctly"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # For local development. For deployment, a Gunicorn server will be used.
    app.run(debug=True, port=5000)
