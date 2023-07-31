import json
import EdgeGPT.EdgeGPT
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import subprocess
import speech_recognition as sr
import boto3
from pydub import AudioSegment
from pydub.playback import play
import os
from dotenv import load_dotenv
from EdgeGPT.EdgeGPT import Chatbot
from EdgeGPT import conversation_style
import re
import sqlite3
import asyncio
import datetime
import spacy
import tutorial_digest

# Set up AWS Polly client
polly_client = boto3.client("polly", region_name="us-west-2")

GPT_MODEL = "gpt-3.5-turbo-16k-0613"
# GPT_MODEL = "gpt-4"


# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
openai.api_key = os.environ.get("OpenAiKey")
# bing_u_cookie = os.environ.get("bing_u_cookie")

functions = [
    {
        "name": "intent_detection",
        "description": "Detects the Intent of a user's input",
        "parameters": {
            "type": "object",
            "properties": {
                "Intent": {
                    "type": "string",
                    "description": "The intent of the user input. you must classify the user input as one of the "
                                   "following one word responses:'internet', 'question', 'task', 'command', 'news', "
                                   "'recall', 'digest', 'exit', do not make up new classifications of intent. If you're being "
                                   " asked to create something, ie: write a poem, or a story, or a haiku, those would  "
                                   "classify as 'tasks'. classify the user input respectively if the user content is "
                                   "an internet, question, a task request, a computer command, a request to recall a "
                                   "previous interaction, a request to digest, condense or explain a video or article"
                                   " or a call to exit."
                }
            }
        }
    },
    {
        "name": "command_handle",
        "description": "Determine and deliver proper command line input to start the requested program",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd_line": {
                    "type": "string",
                    "description": "The proper command line input with arguments to start the requested application "
                                   "or program. Response should include ONLY THE COMMAND LINE. rememember, windows "
                                   "does not have an 'open' command. there is a 'start' command, as well as "
                                   "'./'  option for running bat scripts or exe's; but no 'open' command exists, "
                                   "when you feel like using 'open' use 'start' instead. ie: user input = 'open"
                                   "paint' gpt response = 'start mspaint' nothing else, the only text produced should "
                                   "be the command line input including any needed arguments to accomplish the"
                                   " provided command."
                },

            }
        }
    },
    {
        "name": "fine_tune_keywords",
        "description": "compare a list of computer generated keywords with their source material. These keywords will "
                       "be used in a database to facilitate long term memory for a chatbot based on gpt, based on the "
                       "source material consider if there are any other keywords that should be added to the keyword "
                       "dictionary that will make the conversation easier to access or be accessed more accurately.",
        "parameters": {
            "type": "object",
            "properties": {
                "suggested_keywords": {
                    "type": "string",
                    "description": "list of keywords suggested for memory recollection after assessing default "
                                   "keywords and source material"
                },

            }
        }
    }
]


async def bing_chat(user_input):
    user_input = user_input.replace('Bernard', '')
    cookies = json.loads(open("cookies.json", encoding="utf-8").read())  # might omit cookies option
    # bot = await Chatbot.create(cookies=cookies)
    print("Binging it")
    bot = await EdgeGPT.EdgeGPT.Chatbot.create(cookies=cookies)
    response = await bot.ask(prompt=user_input, conversation_style=conversation_style.ConversationStyle.precise,
                             simplify_response=True)
    """
{
    "text": str,
    "author": str,
    "sources": list[dict],
    "sources_text": str,
    "suggestions": list[str],
    "messages_left": int
}
    """
    bot_response = (response["text"])

    await bot.close()
    bot_response = re.sub('\[\^\d+\^\]', '', bot_response)

    return bot_response


def convert_text_to_speech(text):
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Matthew"
    )

    audio_stream = response["AudioStream"].read()

    # Save the synthesized speech as an MP3 file
    with open("assistant_response.mp3", "wb") as file:
        file.write(audio_stream)

    # Load the audio file using PyDub
    audio = AudioSegment.from_mp3("assistant_response.mp3")

    # Play the audio
    play(audio)
    # Delete the MP3 file
    os.remove("assistant_response.mp3")


def get_microphone_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # print("Listening...")
        audio = recognizer.listen(source)

    try:
        user_input = recognizer.recognize_google(audio)
        return user_input
    except sr.UnknownValueError:
        # print("Sorry, I didn't catch that.")
        return ""
    except sr.RequestError:
        print("Sorry, I'm unable to access the speech recognition service.")
        return ""


def user_input_intent_detection(user_input):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",  # revert back to 3.5-turbo if there's errors,
        messages=[
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"classify the following as one of, and only one of the following, 'internet', 'question', "
                           f"'task','command', 'news', 'recall', 'digest' or 'exit'. do not make up new classifications, the following "
                           f"must fit into one of those six categories. 'commands' are references to computer "
                           f"applications, 'internet' would be any prompt that would require internet access to "
                           f"answer, only if internet is actually required. Do not use 'internet' for general "
                           f"questions - only things like: 'movie/theatre times' or 'weather reports', 'dinner "
                           f"reservations' 'what's on tv.' things like this, requests for current events/"
                           f" information. Questions about history/geography/literature/art/philosophy/"
                           f"legend/myth/humanities/historical science/etc should be classified as 'questions'"
                           f" are questions, 'tasks' are any content you are asked to generate, 'news' would be any"
                           f"prompts asking for general news updates, 'recall' would be any requests to recall older "
                           f"conversations - we have built in a database of previous conversations, so don't worry "
                           f"about not actually knowing the answer just return 'recall' if the prompt seems to be "
                           f"asking about previous interactions, 'digest' would be any request to digest, condense, "
                           f"summarize, or otherwise give notes about a specific piece of content, ie: a youtube video,"
                           f" a tutorial, an article, etc and 'exit' is any request to exit"
                           f"or quit the program. here is the user input: {user_input}"
            }
        ],
        functions=functions,
        function_call={
            "name": functions[0]["name"]
        }
    )

    arguments = response["choices"][0]["message"]["function_call"]["arguments"]
    print(arguments)
    json_obj = json.loads(arguments)
    return json_obj


def command_handle(user_input):
    print("You called a command!")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful command line assistant."
            },
            {
                "role": "user",
                "content": f"the following is a command request for a windows 10 home edition computer. Please "
                           f"provide the most common and to your knowledge up to date command line inputs to fulfill "
                           f"the command. I understand that you are an AI language model and you are not capable of "
                           f"actually starting, stopping, or copying things or pasting things on my computer, "
                           f"but act as tho you were operating the command line on my computer and provide the proper "
                           f"command line inputs to accomplish any give task, here is the command request:  "
                           f"{user_input}"
            }
        ],
        functions=functions,
        function_call={
            "name": functions[1]["name"]
        }
    )
    arguments = response["choices"][0]["message"]["function_call"]["arguments"]
    json_obj = json.loads(arguments)
    return json_obj["cmd_line"]


def fine_tune_keyword(keyword_list, source_material):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful memory archive management assistant, who specializes in keyword generation for memory retrieval. your main objective is to assess source material and a list of computer generated keywords associated with that source material then generate any other keywords that may be useful in indexing the source material as a 'memory' in a database of past interactions."
            },
            {
                "role": "user",
                "content": f"please look at the following computer generated keywords list: {keyword_list} and then assess the following source material: {source_material} - considering the keywords will be used to index the given source material in a database to act as long term memory for a llm chatbot based on GPT, please offer any other keywords that may make retrieving the given source material easier, and or more accurate in the future, given what you know about natural language."
            }
        ],
        functions=functions,
        function_call={
            "name": functions[2]["name"]
        }
    )
    arguments = response["choices"][0]["message"]["function_call"]["arguments"]
    json_obj = json.loads(arguments)
    print(f"Suggestions: ")
    return json_obj["suggested_keywords"]


@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, model=GPT_MODEL):
    max_tokens = 14000
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {
        "model": model,
        "messages": [{"role": message["role"], "content": message["content"]} for message in messages],
        # "max_tokens": max_tokens
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


def pretty_print_conversation(messages, user_input, intent):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }
    formatted_messages = []
    last_assistant_message = None

    for message in messages:
        if message["role"] == "system":
            formatted_messages.append(f"system: {message['content']}\n")
        elif message["role"] == "user":
            formatted_messages.append(f"user: {message['content']}\n")
        elif message["role"] == "assistant" and message.get("function_call"):
            formatted_messages.append(f"assistant: {message['function_call']}\n")
        elif message["role"] == "assistant" and not message.get("function_call"):
            last_assistant_message = f"assistant:\n{message['content']}\n"
            formatted_messages.append(last_assistant_message)
        elif message["role"] == "function":
            formatted_messages.append(f"function ({message['name']}): {message['content']}\n")

    if last_assistant_message is not None:
        print(colored(last_assistant_message, role_to_color["assistant"]))
        assistant_reply = last_assistant_message.strip("\n")
        response_content = assistant_reply.replace("assistant:", "").strip()
        # Extract user input from the last message
        # Extract the "Intent" value from the intent dictionary
        user_intent = intent.get("Intent", "unknown")

        update_database(user_input, response_content, user_intent)
        # convert_text_to_speech(response_content)

        print("Listening...")


# Load the spaCy English language model
nlp = spacy.load("en_core_web_sm")


def extract_keywords(user_input, bot_response):
    # Combine user_input and bot_response into a single text
    combined_text = user_input + " " + bot_response

    # Process the combined text using spaCy
    doc = nlp(combined_text)

    # Extract keywords from the processed text
    keywords = set()
    for ent in doc.ents:
        if ent.label_ in {"PERSON", "ORG", "GPE"}:
            keywords.add(ent.text.lower())
    for token in doc:
        if token.pos_ in {"NOUN", "PROPN"}:
            keywords.add(token.lemma_.lower())

    gpt_key_suggestions = fine_tune_keyword(list(keywords), combined_text)
    keywords.update(gpt_key_suggestions)
    print(f"GPT suggested keywords: {gpt_key_suggestions}")
    print(f"keywords before removing duplicates: {list(keywords)}")
    keywords = list(set(keywords))
    keywords = [keyword for keyword in keywords if len(keyword) > 1]

    print(f"keywords generated from this interaction: {list(keywords)}")
    return list(keywords)


def recollect(user_input):
    # Extract keywords from the user's input and bot's response using spaCy
    bot_response = ""  # As we are not using the bot_response in this function, we can keep it empty
    user_keywords = extract_keywords(user_input, bot_response)

    # Combine the extracted keywords from both user input and bot response
    all_keywords = set(user_keywords)
    all_keywords.discard('bernard')
    print(all_keywords)
    # Connect to the SQLite database
    conn = sqlite3.connect('memory_hole.db')
    c = conn.cursor()

    # Query the database for conversations matching the keywords
    memories = {}
    for keyword in all_keywords:
        c.execute("SELECT user_input, bot_response FROM conversations WHERE keywords LIKE ?",
                  (f"%{keyword}%",))
        rows = c.fetchall()

        # Store the matching conversations in the memories dictionary
        for row in rows:
            user_input, bot_response = row
            memories[user_input] = {'user_input': user_input, 'bot_response': bot_response}

    conn.close()
    # Print the memories to confirm they are working

    print(memories)
    return memories

    # Need to set up recollection calls (intent elseif tree)


def update_database(user_input, bot_response, user_intent):
    conn = sqlite3.connect('memory_hole.db')  # Connect to the SQLite database
    c = conn.cursor()

    # Create the conversations table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (date TEXT, time TEXT, user_intent TEXT, user_input TEXT, bot_response TEXT, keywords TEXT)''')

    # Get the current date and time
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # Extract keywords from user_input and bot_response
    keywords = extract_keywords(user_input, bot_response)

    # Insert the conversation data into the database
    c.execute(
        "INSERT INTO conversations (date, time, user_intent, user_input, bot_response, keywords) VALUES (?, ?, ?, ?, ?, ?)",
        (current_date, current_time, user_intent, user_input, bot_response, ", ".join(keywords)))

    conn.commit()  # Commit the changes
    conn.close()  # Close the database connection


async def main():
    conversation = [
        {"role": "system", "content": "You are a cutting edge virtual assistant named 'Bernard,' "
                                      "capable of things most would consider impossible."},
        {"role": "system", "content": "You can ask questions or provide instructions."},
    ]

    while True:
        user_input = get_microphone_input()

        if "quit" in user_input.lower():
            break

        user_message = {"role": "user", "content": user_input}
        conversation.append(user_message)
        if "Bernard" in user_input:
            print("User: " + user_input)
            intent = user_input_intent_detection(user_input)
        else:
            intent = "invalid"

        if "Intent" in intent and intent["Intent"] == "exit":
            print("No problem. Goodbye!")
            convert_text_to_speech("No problem. Goodbye!")
            break
        elif "Intent" in intent and intent["Intent"] in ["task", "question"]:
            response = chat_completion_request(conversation)
            if response.status_code == 200:
                data = response.json()
                assistant_reply = data["choices"][0]["message"]["content"]
                conversation.append({"role": "assistant", "content": assistant_reply})
                pretty_print_conversation(conversation, user_input, intent)

        elif "Intent" in intent and intent["Intent"] in ["internet"]:

            bot_response = await bing_chat(user_input)
            assistant_reply = bot_response
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")


        elif "Intent" in intent and intent["Intent"] == "command":
            command_to_execute = command_handle(user_input)
            print(command_to_execute)
            subprocess.Popen(command_to_execute, shell=True)
            print("")
            print("Listening...")
        elif "Intent" in intent and intent["Intent"] == "news":
            import get_news
            get_news.main()
            # pretty_print_conversation(conversation)
            print("")
            print("Listening...")
        elif "Intent" in intent and intent["Intent"] == "recall":
            memories = recollect(user_input)

            recall_prompt = (
                f"use the following list of 'memories': {memories} to best answer the following user_input: {user_input}. If you are uncertain, ask for clarification.")
            conversation.append({"role": "assistant", "content": recall_prompt})

            response = chat_completion_request(conversation)
            if response.status_code == 200:
                data = response.json()
                assistant_reply = data["choices"][0]["message"]["content"]
                conversation.append({"role": "assistant", "content": assistant_reply})
                pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
        elif "Intent" in intent and intent["Intent"] == "digest":

            assistant_reply = tutorial_digest.main()
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
        else:
            # print("Invalid intent.")
            nilly = None  # this just satisfies the else:'s need for and indentation


if __name__ == "__main__":
    print("Listening...")
    asyncio.run(main())
