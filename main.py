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

# Set up AWS Polly client
polly_client = boto3.client("polly", region_name="us-west-2")

#GPT_MODEL = "gpt-3.5-turbo-0613"
GPT_MODEL = "gpt-4"


# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
openai.api_key = os.environ.get("OpenAiKey")
#bing_u_cookie = os.environ.get("bing_u_cookie")

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
                                   "following one word responses:'internet', 'question', 'task', 'command', 'exit', do not make "
                                   "up new classifications of intent. If you're being asked to create something, "
                                   "ie: write a poem, or a story, or a haiku, those would classify as 'tasks'. "
                                   "classify the user input respectively if the user content is an internet, question, "
                                   "a task request, a computer command, or a call to exit."
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
                                   "does not have an 'open' command. there is a 'start' command, as well as './' option "
                                   "for running bat scripts or exe's; but no 'open' command exists, when you feel like "
                                   "using 'open' use 'start' instead. ie: user input = 'open"
                                   "paint' gpt response = 'start mspaint' nothing else, the only text produced should "
                                   "be the command line input including any needed arguments."
                }
            }
        }
    }
]


async def bing_chat(user_input):
    user_input = user_input.replace('Bernard', '')
    cookies = json.loads(open("cookies.json", encoding="utf-8").read())  # might omit cookies option
    #bot = await Chatbot.create(cookies=cookies)
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
        #print("Listening...")
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
        model="gpt-4", #"gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"classify the following as one of, and only one of the following, 'internet', 'question', "
                           f"'task','command', or 'exit'. do not make up new classifications, the following must fit"
                           f" into one of those five categories. 'commands' are references to computer applications, "
                           f"'internet' would be any prompt that would require internet access to answer, only if "
                           f"internet is actually required. Do not use 'internet' for general questions - only things "
                           f"like: 'movie/theatre times' or 'weather reports', 'dinner reservations' 'what's on tv.' "
                           f"things like this, requests for current events/ information. Questions about "
                           f"history/geography/literature/art/philosophy/legend/myth/humanities/historical science/etc"
                           f"should be classified as 'questions' are questions, 'tasks' are any content you are asked "
                           f"to generate, and 'exit' is any request to exit or quit the program. here is the user "
                           f"input: {user_input}"
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
        model="gpt-4",#"gpt-3.5-turbo-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"{user_input}"
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


@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, model=GPT_MODEL):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {
        "model": model,
        "messages": [{"role": message["role"], "content": message["content"]} for message in messages],
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


def pretty_print_conversation(messages):
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
        convert_text_to_speech(response_content)
        print("Listening...")

async def main():
    conversation = [
        {"role": "system", "content": "You are a cutting edge virtual assistant capable of things most would consider "
                                      "impossible."},
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
            break
        elif "Intent" in intent and intent["Intent"] in ["task", "question"]:
            response = chat_completion_request(conversation)
            if response.status_code == 200:
                data = response.json()
                assistant_reply = data["choices"][0]["message"]["content"]
                conversation.append({"role": "assistant", "content": assistant_reply})
                pretty_print_conversation(conversation)

        elif "Intent" in intent and intent["Intent"] in ["internet"]:

            bot_response = await bing_chat(user_input)
            assistant_reply = bot_response
            conversation.append({"role": "assistant", "content": assistant_reply})
            pretty_print_conversation(conversation)


        elif "Intent" in intent and intent["Intent"] == "command":
            command_to_execute = command_handle(user_input)
            print(command_to_execute)
            subprocess.Popen(command_to_execute, shell=True)
        else:
            #print("Invalid intent.")
            nilly = None  # this just satisfies the else:'s need for and indentation


if __name__ == "__main__":
    import asyncio
    print("Listening...")
    asyncio.run(main())
#   sys.exit(0)
