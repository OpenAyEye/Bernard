import os
import datetime
from pocketsphinx import LiveSpeech
import pyttsx3

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
    engine = pyttsx3.init()

    print("Listening... (Say 'quit dictation' to stop dictation)")

    # Start the loop to capture audio and perform speech recognition
    text = ""
    for phrase in LiveSpeech():
        recognized_text = str(phrase)

        if "quit dictation" in recognized_text.lower():
            print("Dictation Ended.")
            save_dictation_to_file(text)
            return text

        text += recognized_text + " "
        print(recognized_text, end=" ")

if __name__ == "__main__":
    main()
