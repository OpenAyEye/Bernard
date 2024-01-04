import requests
from bs4 import BeautifulSoup
import openai
import os
from dotenv import load_dotenv


def search_web(query, api_key):
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": 10}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []

    search_results = response.json().get('webPages', {}).get('value', [])
    return [{'title': result['name'], 'url': result['url'], 'snippet': result['snippet']} for result in search_results]


def scrape_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return ""

    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text()


def create_search_file(search_results):
    with open('search_results_temp.txt', 'w', encoding='utf-8') as file:
        for result in search_results:
            file.write(f"Title: {result['title']}\n")
            file.write(f"URL: {result['url']}\n")
            file.write("Content:\n")
            content = scrape_content(result['url'])
            file.write(content)
            file.write("\n" + "#" * 50 + "\n")


#######################################################TEST
import openai
import time

def process_query_and_respond(file_path, query):
    from openai import OpenAI
    import os
    import time
    import re
    global messages
    from dotenv import load_dotenv
    import openai
    from openai import OpenAI
    #user_input = "can you give me the movie show times for houghton michigan for today, 1/3/2024"
    load_dotenv("config.env")
    # Access the OpenAI key from the environment variable
    openai.api_key = os.environ.get("OpenAiKey")

    client = OpenAI()
    #file_path = 'search_results_temp.txt'
    file = client.files.create(
        file=open(file_path, "rb"),
        purpose='assistants'
    )
    file_id = file.id
    print(f"File Info:\n {file}\n")

    # Create an assistant with retrieval enabled

    # Add the file to the assistant

    assistant = client.beta.assistants.create(
        instructions="You are a web search results analyzer who answers questions based on websearch results stored "
                     "in a text file.",
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
        content=f"I need you respond to the following user input using the file uploaded earlier{query}"
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
                cleaned_content = re.sub(r"【\d+†source】", "", content)
                cleaned_content = cleaned_content.strip()
                print(cleaned_content)
                return cleaned_content
            else:
                print("No messages received.")
            # break
            time.sleep(1)
            # print(messages.data. content[0].text.value)
            break
        else:
            print("Run is in progress - Please Wait")
            continue
def process_query_and_respond_bak(file_path, query,
                              instructions="You are a customer support chatbot. Use your knowledge base to best respond to customer queries.",
                              model="gpt-4-1106-preview"):
    from openai import OpenAI
    client = OpenAI()
    # Upload the file for retrieval
    file = client.files.create(
        file=open(file_path, "rb"),
        purpose='assistants'
    )
    file_id = file.id
    print(f"File Info:\n {file}\n")

    # Create an assistant with retrieval enabled

    # Add the file to the assistant
    assistant = client.beta.assistants.create(
        instructions="You are a web search results analyzer who answers questions based on websearch results stored "
                     "in a text file.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        file_ids=[file_id]
    )
    print(f"Assistant Info:\n {assistant}\n")
    assistant_id = assistant.id

    # Send a query to the assistant and get a response
    try:
        # Create the thread
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": f"please analyze these search results and answer the user input here: {query}",
                    "file_ids": [file_id]
                }
            ]
        )
        thread_id = thread.id
        print(f"Thread Info:\n {thread}\n")

        # Create the run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        run_id = run.id

        # Poll for the run completion and retrieve the response
        while True:
            completed_run = client.beta.threads.runs.retrieve(run_id=run_id, thread_id=thread_id)
            print(f"status: {completed_run}")
            if completed_run.status == 'completed':  # Check if the run has completed
                break
            time.sleep(1)  # Wait for a second before polling again

        # Extracting the response from the completed run
        print(f"response:\n {completed_run}")
        response = completed_run.choices[0].message.text.strip()
        print(f"Response from GPT:\n{response}")

        return response

    except openai.APIError as e:
        return f"Error in processing query: {e}"

    except openai.APIError as e:
        return f"Error in processing query: {e}"

def main(search_query):
    # Initialize OpenAI API key
    load_dotenv("config.env")
    openai.api_key = os.environ.get("OpenAiKey")
    # Example Usage
    api_key = os.environ.get("bing_api")

    search_results = search_web(search_query, api_key)
    print(f"Search Results:\n {search_results}\n")
    if search_results:
        create_search_file(search_results)
        search_results_path = 'search_results_temp.txt'
        response = process_query_and_respond(search_results_path, search_query)
        print(f"Response: \n{response}\n")
        return response

    else:
        error_text = "no search results found :("
        print(error_text)
        return error_text


if __name__ == "__main__":
    search_query = "can you give me the forcast for houghton michigan for tomorrow, 1/4/2024"  # input("Enter your search query: ")
    response = main(search_query)
    print(f"The Response\n {response}")