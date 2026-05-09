import sqlite3

# --- Configuration ---
# This script is for running ad-hoc queries against your ratings database.
# By default, it connects to the elo_ratings.sqlite database.
DB_PATH = "elo_ratings.sqlite"

def q(query, db_path=DB_PATH):
    """
    Executes a SQL query and prints the results without external libraries.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            rows = cursor.fetchall()
            
            if not rows:
                print("Query returned no results.")
                return

            # Get column names from cursor description
            headers = [description[0] for description in cursor.description]
            
            # Calculate the maximum width for each column
            col_widths = [len(h) for h in headers]
            for row in rows:
                for i, cell in enumerate(row):
                    cell_len = len(str(cell))
                    if cell_len > col_widths[i]:
                        col_widths[i] = cell_len
            
            # Print header
            header_line = " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers)))
            print(header_line)
            
            # Print separator
            separator_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
            print(separator_line)
            
            # Print rows
            for row in rows:
                row_line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
                print(row_line)
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- Main Query ---
# Place the SQL query you want to run inside the triple quotes.
# The last query I helped you with is here by default.
if __name__ == "__main__":
    # q("""
    #     SELECT run_id,
    #         log_loss,
    #         brier,
    #         ece,
    #         mean_uncertainty,
    #         median_uncertainty,
    #         std_uncertainty,
    #         pct_u_max,
    #         pct_u_min

    #     FROM run_metadata
    #     ORDER BY run_id DESC;
    # """)

    q("""
        SELECT run_id,
               w2,
               iterations,
               created_at
        FROM whr_run_metadata
        ORDER BY created_at DESC;
    """)