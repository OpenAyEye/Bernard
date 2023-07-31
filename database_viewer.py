import sqlite3

def display_database_contents():
    # Connect to the SQLite database
    conn = sqlite3.connect('memory_hole.db')
    c = conn.cursor()

    try:
        # Fetch all rows from the 'conversations' table
        c.execute("SELECT * FROM conversations")
        rows = c.fetchall()

        # Print the column headers
        print("date\t\ttime\t\tuser_intent\t\tuser_input\t\tbot_response\t\tkeywords")
        print("----------------------------------------------------------------------------")

        # Print the contents of the 'conversations' table
        for row in rows:
            date, time, user_intent, user_input, bot_response, keywords = row
            print(f"{date}\t{time}\t{user_intent}\t\t{user_input}\t\t{bot_response}\t\t{keywords}")
            #print(f"{user_input} keywords: {keywords}")
    except sqlite3.Error as e:
        print(f"Error: {e}")

    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    display_database_contents()

