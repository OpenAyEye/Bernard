import os
import yt_dlp
import speech_recognition as sr
from dotenv import load_dotenv
import openai
import whisper
import json
from bs4 import BeautifulSoup
import requests
import time




model = whisper.load_model("medium", device="cuda") #Change to "cpu" for CPU

functions = [
    {
        "name": "digest_content",
        "description": "generates detailed hierarchical outlines of content including clarifying notes and commentary.",
        "parameters": {
            "type": "object",
            "properties": {
                "digested_content": {
                    "type": "string",
                    "description": "A comprehensive outline and summary of the content"
                }
            }
        }
    },
{
        "name": "summarize_content",
        "description": "digest content and write verbose detailed lectures on the content provided",
        "parameters": {
            "type": "object",
            "properties": {
                "content_summary": {
                    "type": "string",
                    "description": "A comprehensive, detailed lecture and summary of the content"
                }
            }
        }
    },
]


# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
openai.api_key = os.environ.get("OpenAiKey")
# bing_u_cookie = os.environ.get("bing_u_cookie")

def download_audio(youtube_url, output_dir):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.wav'),  # Specify the filename with .wav extension
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(youtube_url, download=True)
        audio_file_path = ydl.prepare_filename(result)

    # Return the path of the downloaded audio file
    return audio_file_path



def transcribe_audio(AudioFile):


    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(AudioFile)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16=True) # Change to False for CPU. check line 89 for further changes that need to be made for CPU use.
    result = model.transcribe(AudioFile)
    print(result["text"])


    transcription = result["text"]
    #print(transcription)
    return transcription

def content_summary(user_input, outline):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {
                "role": "system",
                "content": "you are a useful essayist. You take content and develop comprehensive lectures to explain "
                           "the content explainer."

            },
            {
                "role": "user",
                "content": f"write a long form, comprehensive and detailed 2000 word essay for computer science : "
                           f"students discussing '{user_input}'." # the lecture needs to cover the following "
                           #f"outline point for point: '{outline}'"


            }
        ],
        #functions=functions,
        #function_call={
        #    "name": functions[1]["name"]
        #},
        max_tokens=10000
    )
    time.sleep(1)
    bot_response = response["choices"][0]["message"]["content"]
    return bot_response
    #arguments = response["choices"][0]["message"]["function_call"]["arguments"]
    #json_obj = json.loads(arguments)
    #print(f"content summary: {json_obj['content_summary']}")
    #return str(json_obj["content_summary"])
def digest_content(user_input):
    print("Digesting Content!")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful note taking assistant. You're an expert in providing comprehensive notes"
                           " using the hierarchical outlines with lots of detail and clarifying commentary."
                           ""
            },
            {
                "role": "user",
                "content": f" write college level notes for the following content, use an outline"
                           f" of hierarchical levels to formate these notes. Go several levels deep,"
                           f" make sure and note the key aspects of the content: {user_input}."

            }
        ],
        functions=functions,
        function_call={
            "name": functions[0]["name"]
        }
    )
    print("content digested.")

    arguments = response["choices"][0]["message"]["function_call"]["arguments"]
    json_obj = json.loads(arguments)

    return json_obj["digested_content"]


def scrape_webpage_content(webpage_url):
    response = requests.get(webpage_url)
    if response.status_code != 200:
        print(f"Failed to fetch the webpage: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    main_content_tags = ["p", "h1", "h2", "h3", "h4", "h5", "h6"]

    # Additional filtering criteria
    unwanted_classes = ["menu", "advertisement", "sidebar", "footer", "a", "li"]
    unwanted_tags = ["nav", "aside", "footer", "header", "span", "li class"]
    min_content_length = 50
    max_position_to_include = 5

    clean_text = ""
    for i, tag in enumerate(soup.find_all(main_content_tags)):
        # Exclude elements with certain class names
        if tag.get("class") and any(cls in tag.get("class") for cls in unwanted_classes):
            tag.extract()  # Remove the unwanted tag
            continue

        # Exclude specific tags
        if tag.name in unwanted_tags:
            tag.extract()  # Remove the unwanted tag
            continue

        text = tag.get_text().strip()

        # Exclude elements with content length below the threshold
        if len(text) < min_content_length:
            continue

        # Exclude elements within certain positions in the document
        if i < max_position_to_include:
            continue

        clean_text += f"{text}\n"

    return clean_text




def main():
    #input_url = input("Enter URL: ")
    input_url = "youtube"
    output_dir = "audio_files"  # Change this directory path if you want a different output location
    digested_content = "none"
    summarized_content = "none"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if "youtube" in input_url:
        #audio_file_path = download_audio(input_url, output_dir)
        audio_file_path= "audio_files/ChatGPT as an Interpreter： Introducing the KB Microservice for autonomous AI entities.txt"

        with open(audio_file_path, "r") as file:
            file_content = file.read()
        text = file_content
        #print(audio_file_path)
        #text = transcribe_audio(audio_file_path)
        print("Transcription: ")
        print(text)
        if text is not None:
            text_file_path = os.path.join(os.path.splitext(audio_file_path)[0] + ".txt")
            digested_content = digest_content(text)
            summarized_content = content_summary(text, digested_content)

            with open(text_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(text)
        else:
            print(f"Transcription for {audio_file_path} was unsuccessful.")

        #print("Summary and Outline: ")
        #print("**********************")
        #print(f"Summary: {summarized_content}")
        #print(f"Outline: {digested_content}")
        content_return = f"Outline:\n {digested_content} \nSummary: \n{summarized_content}"
        #print(content_return)
        return content_return
    else:
        print("not a youtube channel, will scrape for text and digest")
        webpage_url = input_url  # Assuming the input is a webpage URL
        webpage_content = scrape_webpage_content(webpage_url)
        digested_content = digest_content(webpage_content)
        summarized_content = content_summary(webpage_content)
        #print("Summary and Outline: ")
        #print("**********************")
        #print(f"Summary: \n{summarized_content}")
        #print(f"Outline: \n{digested_content}")
        # Save the digested content to a text file if needed
        with open("webpage_content.txt", "w", encoding="utf-8") as text_file:
            text_file.write(webpage_content)
        with open("digested_content.txt", "w", encoding="utf-8") as text_file:
            text_file.write(digested_content + " " + summarized_content)

        content_return = f"Outline:\n {digested_content} \nSummary: \n{summarized_content}"
        #print(content_return)
        return content_return

if __name__ == "__main__":
    main()
