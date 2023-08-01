import os
import datetime
import speech_recognition as sr
import pyttsx3
from google.cloud import speech
from dotenv import load_dotenv
# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
creds = os.environ.get("GoogleCredsJson")

credentials_path = creds # use your own downloaded google cloud json file here
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
client = speech.SpeechClient()

def save_dictation_to_file(text):
    date = datetime.datetime.now().strftime("%m%d%Y")
    folder_name = "dictations"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    filename = os.path.join(folder_name, f"dictation-{date}.txt")
    with open(filename, "w") as file:
        file.write(text)
    print(f"Dictation saved to {filename}")


def main():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    engine = pyttsx3.init()

    # Set up the Google Cloud Speech-to-Text client
    client = speech.SpeechClient()

    print("Listening... (Say 'quit dictation' to stop dictation)")

    # Start the loop to capture audio and perform speech recognition
    text = ""
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=5)  # Increase or decrease as needed

                # Convert the audio to a byte stream
                audio_stream = audio.get_wav_data(convert_rate=16000, convert_width=2)

                # Create a RecognitionAudio object from the byte stream
                recognition_audio = speech.RecognitionAudio(content=audio_stream)

                # Create a RecognitionConfig object with enable_word_time_offsets set to True
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code='en-US',
                    enable_word_time_offsets=True
                )

                # Perform speech recognition using the Google Cloud Speech-to-Text API
                response = client.recognize({
                    'config': config,
                    'audio': recognition_audio,
                })

                for result in response.results:
                    for word in result.alternatives[0].words:
                        #print("Word: {}, Timestamp: {}".format(word.word, word.start_time.seconds))
                        print(word.word, end=" ")

                        if "quit dictation" in word.word.lower():
                            print("Dictation Ended.")
                            save_dictation_to_file(text)
                            return text


                        text += word.word + " "

            except sr.UnknownValueError:
                pass
                # print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"Error: {e}")

    engine.stop()



if __name__ == "__main__":
    main()
