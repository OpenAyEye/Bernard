import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
import re
import openai
from openai import OpenAI
global messages

import sqlite3
import csv
import os

# The path where you want to save the CSV file
import sqlite3


def text_to_db(txt_file_path, db_path):
    # Define your database schema based on the original structure
    # This example assumes a simple table as previously described
    create_table_query = '''CREATE TABLE IF NOT EXISTS conversations (
                                date TEXT,
                                time TEXT,
                                memory_index INTEGER,
                                user_intent TEXT,
                                user_input TEXT,
                                bot_response TEXT,
                                keyword TEXT
                            );'''

    # Connect to a new or existing database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the table
    cursor.execute(create_table_query)

    # Open and read the text file
    with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
        # Skip header or process it as needed
        next(txt_file)  # Assuming the first line is a header

        # Read and insert each row
        for line in txt_file:
            # Assuming your data is pipe-separated; adjust as necessary
            columns = line.strip().split(' | ')
            if len(columns) == 7:  # Ensure there are exactly 7 columns, adjust the number based on your actual data structure
                cursor.execute(
                    "INSERT INTO conversations (date, time, memory_index, user_intent, user_input, bot_response, keyword) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    columns)

    # Commit changes and close the database connection
    conn.commit()
    conn.close()


# Example usage



def db_to_text(db_path, txt_file_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Select all data from the conversations table
    cursor.execute("SELECT * FROM conversations")
    rows = cursor.fetchall()

    # Optionally, fetch the column names if you want to include them as a header
    column_names = [description[0] for description in cursor.description]

    # Open the text file for writing
    with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
        # Write the column names as a header, formatted as you like
        header = ' | '.join(column_names) + '\n' + '-'*50 + '\n'
        txt_file.write(header)

        # Iterate over rows and write each to the file in a formatted string
        for row in rows:
            formatted_row = ' | '.join(str(value) for value in row) + '\n'
            txt_file.write(formatted_row)

    print(f"Data exported successfully to {txt_file_path}")

    # Close the database connection
    conn.close()
    return txt_file_path

# Example usage

def db_to_csv(db_path, csv_file_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to select all data from the conversations table
    cursor.execute("SELECT * FROM conversations")
    rows = cursor.fetchall()

    # Fetch the column names
    column_names = [description[0] for description in cursor.description]

    # Get the directory name from the CSV file path
    directory = os.path.dirname(csv_file_path)

    # Check if the directory is not empty and then create it if it doesn't exist
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Write the rows to the CSV file
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(column_names)  # Write the header
        csv_writer.writerows(rows)  # Write the data rows

    print(f"Data exported successfully to {csv_file_path}")

    # Close the database connection
    conn.close()
    return csv_file_path


#######################################################TEST


def recollect(file_path, query):
    client = OpenAI(
        api_key=os.environ.get("OpenAiKey")
    )

    delete_all_temp_files(client)
    delete_all_assistants(client)
    time.sleep(2)

    file = client.files.create(
        file=open(file_path, "rb"),
        purpose='assistants'
    )
    file_id = file.id
    print(f"File Info:\n {file}\n")

    # Create an assistant with retrieval enabled
    import datetime
    # Add the file to the assistant
    time_of_day = datetime.datetime

    assistant = client.beta.assistants.create(
        name="Bernard Memory",
        instructions="you are a memory management assistant, you'll be provided a text file in the format of a database, use this data to respond to users inquiries about about previous conversations.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        file_ids=[file_id]
    )
    print(f"Assistant Info:\n {assistant}\n")
    assistant_id = assistant.id

    assistant = client.beta.assistants.retrieve(f"{assistant_id}")
    print("Assistant Located")

    thread = client.beta.threads.create()
    print("Thread  Created")
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"I need you respond to the following user input using the file uploaded earlier. User Input: {query}. It is currently: {time_of_day}"
    )
    print("Thread Ready")

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    print("Assistant Loaded")
    print("Run Started - Please Wait")

    while True:
        time.sleep(10)

        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        if run_status.status == "completed":
            print("Run is Completed")
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            if messages.data:
                content = messages.data[0].content[0].text.value
                #print(f"The Content: {content}")
                cleaned_content = re.sub(r"【\d+†source】", "", content)
                cleaned_content = cleaned_content.strip()
                # print(cleaned_content)
                # delete_all_temp_files(client)
                return cleaned_content
            else:
                print("No messages received.")
            # break
            time.sleep(1)
            # delete_all_temp_files(client)
            # print(messages.data. content[0].text.value)
            break
        else:
            print("Thinking...")
            continue


def delete_all_assistants(client):
    # Retrieve all assistants
    assistants = client.beta.assistants.list(limit=None)

    # Loop through each assistant and delete
    for assistant in assistants.data:
        try:
            response = client.beta.assistants.delete(assistant.id)
            print(f"Deleted assistant {assistant.id}: {response}")
        except openai.error.OpenAIError as e:
            print(f"Failed to delete assistant {assistant.id}: {e}")


def delete_all_temp_files(client):
    # List all files
    files = client.files.list()

    # Iterate through the files and delete 'search_results_temp.txt'
    for file in files:
        if file.filename == 'BernardBrain.txt':
            try:
                # Delete the file
                client.files.delete(file.id)
                print(f"Deleted file: {file.id} - {file.filename}")
            except Exception as e:
                print(f"Error deleting file {file.id}: {e}")


def main(user_input):

    db_path = 'BernardBrain.db'
    txt_file_path = 'BernardBrain.txt'
    filepath = db_to_text(db_path, txt_file_path)
    # Initialize OpenAI API key
    load_dotenv("config.env")
    openai.api_key = os.environ.get("OpenAiKey")
    # Example Usage
    recollection = recollect(file_path=filepath, query=user_input)
    print(f"The recollection: {recollection}")
    return recollection


if __name__ == "__main__":
    user_input = "can you recall about the average price of a hat designed to block alien death rays....or just bluetooth and wifi :p"  # input("Enter your search query: ")
    response = main(user_input)
    print(f"The Response\n {response}")

''' # Define the path to your database file
    db_path = 'BernardBrain.db'
    txt_file_path = 'BernardBrain.txt'
    filepath = db_to_text(db_path, txt_file_path)
    #filepath = db_to_csv(db_path, csv_file_path)'''

'''
txt_file_path = 'BernardBrain.db'  # Update this to your text file's path
    db_path = 'BernardBrain_fix.db'  # The path for the new or recovered database
    text_to_db(txt_file_path, db_path)

'''