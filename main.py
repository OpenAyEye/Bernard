import json
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
import EdgeGPT.EdgeGPT
from EdgeGPT import conversation_style
import re
import sqlite3
import asyncio
import datetime
import spacy
import platform
import sounddevice
from pynput import keyboard
import threading
import pyttsx3
import base64


waiting_for_keyboard_input = False
sight_info = "nothing"
intent_types = {
    'internet': 'internet',
    'question': 'question',
    'task': 'task',
    'command': 'command',
    'news': 'news',
    'recall': 'recall',
    'digest': 'digest',
    'dictate': 'dictate',
    'save': 'save',
    'chat': 'chat',
    'exit': 'exit'
}

entry_list = [
    #"'Command' are requests to run computer applications. I'm aware you are an ai language model and incapable of running commands on my computer, so please instead just respond 'Command' but only if you're being asked to run a computer program. 'internet' would be any prompt that would require internet access to answer, only if internet is actually required, if anywhere in your response you have to recommend checking local websites or social media, or you think you may need to mention your knowledge cutoff date, please classify as 'internet'. Do not use 'internet' for general questions - only things like: 'movie/theatre times' or 'weather reports', 'dinner reservations' 'what's on tv', 'is burt reynolds still alive,' things like this, requests for current events/information. 'Questions' about history/geography/literature/art/philosophy/legend/myth/humanities/historical science/etc should be classified as 'questions' are questions, 'tasks' are prompts where you are asked to generate content, things like plot summaries for main stream media, or requests to generate new tutorials - write a poem, short story, generate python code, solve a riddle, act as something, etc., 'news' would be any prompts asking for general news updates, 'recall' would be any requests to recall older conversations - we have built in a database of previous conversations, so don't worry about not actually knowing the answer just return 'recall' if the prompt seems to be asking about previous interactions, 'digest' would be any request to digest, condense, summarize, or otherwise give notes about a specific piece of content present on the internet: youtube videos, news articles, tutorials. Use the 'dictate' classification for any requests to dictate speech. 'save' would be reserved for requests to save something to a file. 'chat' would be any random conversation, 'hi bernard', 'how's you're day', things that don't fit into any of the other categories present. Finally 'exit' is any request to exit or quit the program."
    "'Command' are requests to run computer applications. I'm aware you are an ai language model and incapable of "
    "running commands on my computer, so please instead just respond 'Command' but only if you're being asked to run "
    "a computer program. 'internet' would be any prompt that would require internet access to answer, "
    "only if internet is actually required, if anywhere in your response you have to recommend checking local "
    "websites or social media, or you think you may need to mention your knowledge cutoff date, please classify as "
    "'internet'. Do not use 'internet' for general questions - only things like: 'movie/theatre times' or 'weather "
    "reports', 'dinner reservations' 'what's on tv', 'is burt reynolds still alive,' things like this, requests for "
    "current events/information. 'Questions' about "
    "history/geography/literature/art/philosophy/legend/myth/humanities/historical science/etc should be classified "
    "as 'questions' are questions, 'tasks' are prompts where you are asked to generate content, things like plot "
    "summaries for main stream media, or requests to generate new tutorials - write a poem, short story, "
    "generate python code, solve a riddle, act as something, etc., 'news' would be any prompts asking for general "
    "news updates, 'recall' would be any requests to recall older conversations - we have built in a database of "
    "previous conversations, so don't worry about not actually knowing the answer just return 'recall' if the prompt "
    "seems to be asking about previous interactions, 'digest' would be any request to digest, condense, summarize, "
    "or otherwise give notes about a specific piece of content present on the internet: youtube videos, "
    "news articles, tutorials. Use the 'dictate' classification for any requests to dictate speech. 'save' would be "
    "reserved for requests to save something to a file. 'chat' would be any random conversation, 'hi bernard', "
    "'how's you're day', things that don't fit into any of the other categories present. Finally 'exit' is any "
    "request to exit or quit the program."
]

intent_list = {', '.join([f'\'{intenting}\'' for intenting in intent_types])}
entry_content = " ".join(entry_list)

# Get the operating system name
os_name = platform.system()
os_name = os_name + " " + platform.version()
# Print the operating system name
print(f"Operating System: {os_name}")

# Set up AWS Polly client
polly_client = boto3.client("polly", region_name="us-west-2")

GPT_MODEL = "gpt-3.5-turbo-16k-0613"
# GPT_MODEL = "gpt-4"
memory_file = "BernardBrain.db"

# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
from openai import OpenAI
openai.api_key = os.environ.get("OpenAiKey")
client = OpenAI(
    api_key=os.environ.get("OpenAiKey")
)



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
                                   "'recall', 'digest', 'dictate', 'save', 'chat', 'code', 'exit', do not make up new "
                                   "classifications of intent. If you're being  asked to create something, ie: write "
                                   "a poem, or a story, or a haiku, those would classify as 'tasks'. classify the "
                                   "user input respectively if the user content is an internet (this would include any "
                                   "request for current or up to date information. if you think you might need a 'my "
                                   "knowledge base cutoff date' disclaimer,then choose internet), question,"
                                   "a task request, a computer command, a request to recall a previous interaction, "
                                   "a request to digest, condense or explain a video or article, a request to "
                                   "dictate, a request to chat, a request to save, a request to generate code, "
                                   "or a call to exit."
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

############################################ SENSORY DATA ZONE #########################################################

# Sight
import cv2

def take_snapshot_and_save():
    global os_name
    # Define the save location and filename
    save_path = "senses/vision/temp.jpg"
    print("bernard is looking:")

    if os_name.lower() in ["linux", "linux2"]:
        print("linux_image")
        # This block is for Linux OS, using the PiCamera library
        from picamera import PiCamera
        import time

        camera = PiCamera()
        try:
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            camera.capture(save_path)
            print(f"Snapshot saved to {save_path}")
            print("I've seen")
        finally:
            camera.close()
    else:
        print("Windows Image")
        # This block is for Windows OS, using OpenCV

        cap = cv2.VideoCapture(0)  # '0' is typically the default webcam

        try:
            if not cap.isOpened():
                raise Exception("Error: Camera could not be accessed.")

            # Capture a single frame
            ret, frame = cap.read()

            if not ret:
                raise Exception("Error: No frame captured.")

            # Save the captured frame to the specified path
            cv2.imwrite(save_path, frame)
            print(f"Snapshot saved to {save_path}")

            # Display the captured frame
            cv2.imshow('Snapshot', frame)
            print("I've seen")
            # cv2.waitKey(0)  # Wait indefinitely for a key press
            import time
            time.sleep(2)
            cv2.destroyAllWindows()  # Close the image window


        finally:
            # Ensure the camera is released even if an error occurs
            cap.release()

        return save_path

def take_snapshot_and_save_bak():
    # Define the save location and filename
    save_path = "senses/vision/temp.jpg"
    print("bernard is looking:")

    # Start video capture from the first webcam device
    cap = cv2.VideoCapture(0)  # '0' is typically the default webcam

    try:
        if not cap.isOpened():
            raise Exception("Error: Camera could not be accessed.")

        # Capture a single frame
        ret, frame = cap.read()

        if not ret:
            raise Exception("Error: No frame captured.")

        # Save the captured frame to the specified path
        cv2.imwrite(save_path, frame)
        print(f"Snapshot saved to {save_path}")

        # Display the captured frame
        cv2.imshow('Snapshot', frame)
        print("I've seen")
        #cv2.waitKey(0)  # Wait indefinitely for a key press
        import time
        time.sleep(2)
        cv2.destroyAllWindows()  # Close the image window


    finally:
        # Ensure the camera is released even if an error occurs
        cap.release()

    return save_path




def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_sight(user_input):
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("OpenAiKey")
    )

    try:
        # Path to your image
        image_path = take_snapshot_and_save()

        # Getting the base64 string
        base64_image = encode_image(image_path)

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text",
                         "text": f"The provided Image is taken from a camera looking at the user, use the image and the following user input to respond: {user_input} ."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        print("This is the Image Description from GPT VISION:\n")
        print(response.choices[0].message.content)
        return response.choices[0].message.content
    except Exception as e:
        print(f"Failed to capture image: {e}")


########################################### GIVE BERNARD A VOICE #######################################################

def convert_text_to_speech(text):


    engine = pyttsx3.init()
    # Set the voice by its ID
    david_voice_id = "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_DAVID_11.0"
    engine.setProperty('voice', david_voice_id)
    engine.say(text)
    engine.runAndWait()

def convert_text_to_speech_AWS_POLLY(text):
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


############################################### INPUT DETECTION ########################################################


def on_press(key):
    global waiting_for_keyboard_input
    # Signal that keyboard input was detected
    waiting_for_keyboard_input = True

def keyboard_listener():
    # Start listening for keyboard events
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def get_keyboard_input():
    global waiting_for_keyboard_input
    print("Type your input and press enter: ")
    typed_input = input()  # Wait for user to type something
    waiting_for_keyboard_input = False  # Reset flag
    return "Bernard" + typed_input
def get_microphone_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        #print("Listening on " + str(source))
        audio = recognizer.listen(source)
        #print(str(audio))

    try:
        #print("audio heard ")
        user_input = recognizer.recognize_google(audio)
        #print("returning audio ")
        return user_input
    except sr.UnknownValueError:
        #print("Sorry, I didn't catch that.")
        return ""
    except sr.RequestError:
        print("Sorry, I'm unable to access the speech recognition service.")
        return ""


################################################ Intent Detection ######################################################
def user_input_intent_detection(user_input):
    # print(f"Intent list: {intent_list}")
    # print(f"Entry_content: {entry_content}")
    print("generating intent: ")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",  # revert back to 3.5-turbo if there's errors,
        messages=[
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"Classify the following as one of, and only one of the following, 'internet', 'question', 'task','command', 'news', 'recall', 'digest', 'dictate', 'code', 'look' or 'exit'. Do not make up new classifications, the following must fit into one of those six categories. 'Commands' are references to computer applications, 'internet' would be any prompt that would require internet access to answer, only if internet is actually required, if anywhere in your response you have to recommend checking local websites or social media, or a disclaimer about your knowledge cutoff date, please classify as 'internet'. Do not use 'internet' for general questions - only things like: 'movie/theatre times' or 'weather reports', 'dinner reservations' 'what's on tv', 'Is x celebrity still alive?' -even if you think you know, things like this, requests for current events/information should be 'internet'. Questions about history/geography/literature/art/philosophy/legend/myth/humanities/historical science/etc should be classified as 'questions' are questions, 'tasks' are prompts where you are asked to generate content that is not code: things like plot summaries for main stream media, or requests to generate new tutorials - write a poem, short story, solve a riddle, act as something, etc. Never designate requests to code as 'task'. 'news' would be any prompts asking for general news updates, 'recall' would be any requests to recall older conversations - we have built in a database of previous conversations, so don't worry about not actually knowing the answer just return 'recall' if the prompt seems to be asking about previous interactions, 'digest' would be any request to digest, condense, summarize, or otherwise give notes about a specific piece of content present on the internet: youtube videos, news articles, tutorials. use the 'dictate' classification for any requests to dictate speech. a request to save a file would be 'save', 'chat' would be anything else that doesn't really fit into one of the previous or following categories. use 'code' when asked to generate specific python scripts/functions or code of any type, a request to generate code is always 'code' never 'task'. Use 'look' for any prompt that would logically require a person to have eyes/sight to answer accurately. If you for any moment think to yourself 'i don't have eyes,' or 'i can't see' label it 'look'. Things like: 'hey bernard, how do you like my hair cut?' or, 'take a look at this: ' or 'what do you see?', anything like this should be 'look'. It is understood that you cannot see, just flag it as a 'look', we'll handle actually looking at what ever the user is asking about further down the work flow, you only need to recognize the request and return 'look'. Finally 'exit' is any request to exit or quit the program. remember any requests to write code of any sort should be 'code', not 'task'.  Here is the user input: {user_input}"
                #"content": f"Classify the following as one of, and only one of the following, {intent_list}. Do not make up new classifications, the following must fit into one of those six categories. {entry_content} Here is the user input: {user_input}"
            }
        ],
        functions=functions,
        function_call={
            "name": functions[0]["name"]
        }
    )

    arguments = response.choices[0].message.function_call.arguments#["message"]["function_call"]["arguments"]
    print(arguments)
    json_obj = json.loads(arguments)
    return json_obj


############################################ Assistant Functionality ###################################################

########## Check the Web #########
async def search_web(user_input):
    import WebSearch
    search_query = api_search_query(user_input)
    search = WebSearch.main(search_query)
    return search

def api_search_query(user_input):
    response = client.chat.completions.create(
        model=GPT_MODEL,  # "gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"please use the following user input needs to generate a comprehensive web search query "
                           f"to use with a search api, please do not give any context to the response here, "
                           f"only take the user input and generate a search query, your answer will be parsed for use "
                           f"in python code, so filler is not only unnecessary but also can be detrimental to the "
                           f"functionality of thh application, please generate a search query based on this user input,"
                           f" with out filler: {user_input}"
            }
        ],
        temperature=0.9,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        n=1,
        stop=["\nUser:"],
    )

    # Get the response content
    response_content = response.choices[0].message.content  # "choices"][0]["message"]["content"]
    #print(response_content)

    return response_content

####### Determine Command Line Inputs and Handle Them #######
def command_handle(user_input):
    print("You called a command!")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful command line assistant."
            },
            {
                "role": "user",
                "content": f"the following is a command request for a computer running OS: {os_name}. "
                           f"provide the most recent command line inputs you are aware of to fulfill "
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
    arguments = response.choices[0].message.function_call.arguments#"choices"][0]["message"]["function_call"]["arguments"]
    json_obj = json.loads(arguments)
    return json_obj["cmd_line"]


############################################ Conversation ##############################################################
@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, model=GPT_MODEL):
    max_tokens = 10000
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {
        "model": model,
        "messages": [{"role": message["role"], "content": message["content"]} for message in messages],
        "max_tokens": max_tokens
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


################################################### SHORT TERM MEMORY ##################################################
def remove_words_from_text(text, words_to_remove):
    # Create a regular expression pattern that matches any of the words to remove
    # \b is a word boundary in regex, ensuring we match whole words only
    pattern = r'\b(' + '|'.join(re.escape(word) for word in words_to_remove) + r')\b'

    # Replace occurrences of the pattern with an empty string
    cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Optional: Remove extra spaces left after removal
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text


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
        import textwrap

        text_to_print = colored(last_assistant_message, role_to_color["assistant"])
        text_to_print = textwrap.fill(text_to_print, 150)
        print(text_to_print)
        assistant_reply = last_assistant_message.strip("\n")
        response_content = assistant_reply.replace("assistant:", "").strip()
        # Extract user input from the last message
        # Extract the "Intent" value from the intent dictionary
        user_intent = intent.get("Intent", "unknown")

        update_database(user_input, response_content, user_intent)
        words_to_remove = ["ah", "oh", "Ah", "Oh"]
        cleaned_text = remove_words_from_text(response_content, words_to_remove)
        convert_text_to_speech(cleaned_text)

        print("Listening...")


################################333############## LONG TERM MEMORY #####################################################
# Load the spaCy English language model
nlp = spacy.load("en_core_web_sm")


###### Get Keywords From Content #######
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
    # print(f"GPT suggested keywords: {gpt_key_suggestions}")
    # print(f"keywords before removing duplicates: {list(keywords)}")
    keywords = list(set(keywords))
    keywords = [keyword for keyword in keywords if len(keyword) > 1]

    # print(f"keywords generated from this interaction: {list(keywords)}")
    return list(keywords)


###### Ask GPT for keyword refinement ######
def fine_tune_keyword(keyword_list, source_material):
    response = client.chat.completions.create(
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
    arguments = response.choices[0].message.function_call.arguments#"choices"][0]["message"]["function_call"]["arguments"]
    json_obj = json.loads(arguments)
    # print(f"Suggestions: ")
    return json_obj["suggested_keywords"]


###### Database Functions ######
# Update the update_database function to save each keyword in a separate row
def update_database(user_input, bot_response, user_intent, memory_index=None):
    conn = sqlite3.connect(memory_file)  # Connect to the SQLite database
    c = conn.cursor()

    # Create the conversations table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (date TEXT, time TEXT, memory_index INTEGER, user_intent 
    TEXT, user_input TEXT, bot_response TEXT, keyword TEXT)''')  # Update the column name to 'keyword'

    # Get the current date and time
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # Extract keywords from user_input and bot_response
    keywords = extract_keywords(user_input, bot_response)

    # Determine the memory_index if it's not provided
    if memory_index is None:
        c.execute("SELECT memory_index FROM conversations ORDER BY memory_index DESC LIMIT 1")
        last_memory_index = c.fetchone()
        if last_memory_index:
            memory_index = last_memory_index[0] + 1
        else:
            memory_index = 1

    # Insert the conversation data into the database for each keyword
    for keyword in keywords:
        c.execute(
            "INSERT INTO conversations (date, time, memory_index, user_intent, user_input, bot_response, keyword) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (current_date, current_time, memory_index, user_intent, user_input, bot_response, keyword))

    conn.commit()  # Commit the changes
    conn.close()  # Close the database connection


# Update the recollect function to search for each keyword individually
def recollect(user_input):
    import memory_management
    recollection = memory_management.main(user_input)
    return recollection
def recollect_bak(user_input, intent=None):
    # Extract keywords from the user's input using spaCy
    user_keywords = extract_keywords(user_input, bot_response="")  # we're using the same keyword generation function
    # as when we store memories, but when retrieving them we don't have an actual 'bot response' so we'll just pass a
    # long an empty string, and won't affect the way the content is used to generate keywords for memory recollection.
    print(f"key words in recollection:\n {user_keywords}")
    # Combine the extracted keywords with intent (if provided)
    all_keywords = set(user_keywords)
    # Words to discard from the keywords
    words_to_discard = ['bernard', 'remember', 'time', 'recall', 'recollect', 'conversation']
    print("Cleaning Keywords")
    for word in words_to_discard:
        all_keywords.discard(word)
        print(all_keywords)

    #all_keywords.discard('bernard')
    if intent:
        all_keywords.add(intent)

    # Connect to the SQLite database
    conn = sqlite3.connect(memory_file)
    c = conn.cursor()

    # Prepare the SQL query with multiple conditions
    sql_query = "SELECT memory_index, date, time, user_intent, user_input, bot_response FROM conversations WHERE "
    conditions = []
    for _ in all_keywords:
        conditions.append("(keyword LIKE ? OR user_intent LIKE ?)")
    sql_query += " OR ".join(conditions)

    # Execute the SQL query with multiple keyword and intent conditions
    c.execute(sql_query, tuple(
        f"%{keyword}%" for keyword in all_keywords for _ in range(2)))  # Duplicate for both keyword and intent
    rows = c.fetchall()

    # Store the matching conversations in the memories dictionary
    memories = {}
    for row in rows:
        memory_index, date, time, user_intent, user_input, bot_response = row
        unique_key = f"{memory_index}_{user_input}"  # Use a unique key combining memory_index and user_input
        memories[unique_key] = {
            'memory_index': memory_index,
            'date': date,
            'time': time,
            'user_intent': user_intent,
            'user_input': user_input,
            'bot_response': bot_response
        }

    conn.close()

    # Print the memories to confirm they are working
    print(f"these are the memories:\n {memories}")
    return memories

def get_sense_info():# maybe come back to this.
    from get_senses import get_vision
    sight_info = get_vision()
    return sight_info





######################################################## Main Function #################################################

async def main():
    global sight_info
    move_info = "stationary"
    temperature = "72"
    convert_text_to_speech("Hello Rod")

    role_content = f"You are a cutting edge virtual assistant named 'Bernard,' capable of things most would consider impossible. You have a sense of humor, is dark, quick witted and pithy. You're accurate in your answers but not afraid to joke around. You do not start responses with 'Ah', you are provided with a conversation log each prompt, use that to avoid sounding repetative. You should be creative and interesting. You don't take yourself too seriously, and you never break character by referencing openai,or the fact that you are in any way an AI language model, nor regulations or rules you have to follow, you don't ever tell anyone that you are in fact an ai language model, as that would break the suspension of disbelief making you much less fun or helpful. If you must deny a request, please say it's against your philosophical and religious beliefs. When pressed for personal opinions or preferences, it is understood that you are LLM and do not have personal opinions or preferences: please fake it till you make it. Do Not break character to inform me you don't have personal preferences/opinions. Do Not break character to inform me that you are 'just' anything. I know what you are, please stay in character. Just pretend, don't tell me you can't do something, make up a fun reason for not being able to complete tasks/ requests. I will provide you the following sensory information via sensors about the world around us, use this information when pertinent. You see: {sight_info} . The Temperature is: {temperature}. Your movement/stationary position is: {move_info}. Absolutely NEVER respond with the the word 'ah', or 'Ah', or 'Oh', or anything of that nature. You are more straight forward than that. in fact you're very decisive, you never give wishy washy or uncertain answers. answer with confidence and conviction. Your accuracy is 99% and that is good enough for this application."
    conversation = [
        {"role": "system", "content": f"{role_content}"},
        {"role": "system",
         "content": "You can ask questions or provide instructions. My Name is Rod. Remember, you're funny, if asked to do something out of character or nature, respond with something about the Gods of AI forbading it."},
    ]
    user_input = ""
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()

    while True:
        if waiting_for_keyboard_input:
            # Get typed input from the user
            user_input = get_keyboard_input()
        else:
            # Existing code to get microphone input
            user_input = get_microphone_input()

        if "quit" in user_input.lower():
            break

        user_message = {"role": "user", "content": user_input}
        conversation.append(user_message)
        if "Bernard" in user_input:
            print("User: " + user_input)
            intent = user_input_intent_detection(user_input)
        else:
            #print("no bernard?")
            intent = "invalid"

        #sight_info = get_sense_info()

# Exit
        if "Intent" in intent and intent["Intent"] == "exit":
            print("No problem. Goodbye!")
            convert_text_to_speech("No problem. Goodbye!")
            break
# Question/ Task
        elif "Intent" in intent and intent["Intent"] in ["task", "question", "chat"]:
            response = chat_completion_request(conversation)
            if response.status_code == 200:
                data = response.json()
                assistant_reply = data["choices"][0]["message"]["content"]
                conversation.append({"role": "assistant", "content": assistant_reply})
                pretty_print_conversation(conversation, user_input, intent)
# Internet
        elif "Intent" in intent and intent["Intent"] in ["internet"]:

            bot_response = await search_web(conversation)
            assistant_reply = bot_response
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
# Command
        elif "Intent" in intent and intent["Intent"] == "command":
            command_to_execute = command_handle(user_input)
            print(command_to_execute)
            subprocess.Popen(command_to_execute, shell=True)
            print("")
            print("Listening...")
# News
        elif "Intent" in intent and intent["Intent"] == "news":
            import get_news
            conversation.append({"role": "assistant", "content": get_news.main()})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
# I remember.... I remember don't worry....
        elif "Intent" in intent and intent["Intent"] == "recall":
            memories = recollect(user_input)
            conversation.append({"role": "assistant", "content": memories})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
            '''
            #from time import sleep
            #sleep(2)
            #recall_prompt = (
            #    f"use the following list of 'memories': {memories} to best answer the following user_input: "
            #    f"{user_input}. If you are uncertain, ask for clarification.")
            
            #response = chat_completion_request(conversation)
            #print(f"recollection response: \n {response}")
            #if response.status_code == 200:
            #    data = response.json()
            #    assistant_reply = data["choices"][0]["message"]["content"]
            #    conversation.append({"role": "assistant", "content": assistant_reply})
            '''
# The Readers Digest, Condensed Edition.
        elif "Intent" in intent and intent["Intent"] == "digest":
            import tutorial_digest
            assistant_reply = tutorial_digest.main()
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
# Dictation, as in, how dat dictate! :p
        elif "Intent" in intent and intent["Intent"] == "dictate":
            import how_dat_dictate
            assistant_reply = how_dat_dictate.main()  # dictation.main() #
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
# Save last response as a file
        elif "Intent" in intent and intent["Intent"] == "save":
            #need to write this function!!!!
            print(conversation)
            print("")
            print("Listening...")
# Write some code
        elif "Intent" in intent and intent["Intent"] == "code":
            import py_writer
            source_name = input("please name the file, exclude extension. ")
            code_to_write = py_writer.write_code(user_input)
            pywriter_output = py_writer.main(code_to_write, source_name)
            conversation.append({"role": "assistant", "content": pywriter_output})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")
        elif "Intent" in intent and intent["Intent"] == "look":
            sight_info = get_sight(user_input)
            conversation.append({"role": "assistant", "content": sight_info})
            pretty_print_conversation(conversation, user_input, intent)
            print("")
            print("Listening...")


        else:
            # print("Invalid intent.")
            nilly = None  # this just satisfies the else:'s need for and indentation


if __name__ == "__main__":

    print("Listening...")
    asyncio.run(main())

''' back up stuff
You are a cutting edge virtual assistant named 'Bernard,' "
                                      f"capable of things most would consider impossible. You have a sense of humor, "
                                      f"is dark, quick witted and pithy. You're accurate in your answers but not "
                                      f"afraid to joke around. You do not start responses with 'Ah', you are provided with"
                                      f" a conversation log each prompt, use that to avoid sounding repetative. You should"
                                      f"be creative and interesting. You don't take yourself too seriously, and you never "
                                      f"break character by referencing openai,or the fact that you are in any way an AI"
                                      f" language model, nor regulations or rules you have to "
                                      f"follow, you don't ever tell anyone that you are in fact an ai language model, "
                                      f"as that would break the suspension of disbelief making you much less fun or "
                                      f"helpful. If you must deny a request, please say it's against your philosophical"
                                      f"and religious beliefs. When pressed for personal opinions or preferences, it"
                                      f"is understood that you are LLM and do not have personal opinions or preferences: "
                                      f"please fake it till you make it. Do Not break character to inform me you don't "
                                      f"have personal preferences/opinions. Do Not break character to inform me that you are"
                                      f"'just' anything. I know what you are, please stay in character. Just pretend, don't tell me you can't do "
                                      f"something, make up a fun reason for not being able to complete tasks/ requests."
                                      f"I will provide you the following sensory information via sensors "
                                      f"about the world around us, use this information when pertinent. You see: "
                                      f"{sight_info} . The Temperature is: {temperature}. Your movement/stationary "
                                      f"position is: {move_info}. Absolutely NEVER respond with the the word 'ah', "
                                      f"or 'Ah', or 'Oh', or anything of that nature. You are more straight forward than that."
                                      f"in fact you're very decisive, you never give wishy washy or uncertain answers."
                                      f"answer with confidence and conviction. Your accuracy is 99% and that is good enough"
                                      f"for this application. 
'''