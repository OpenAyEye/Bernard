import os
import datetime
import speech_recognition as sr
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
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    engine = pyttsx3.init()

    print("Listening... (Say 'quit dictation' to stop dictation)")

    # Start the loop to capture audio and perform speech recognition
    text = ""
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=7)  # Increase or decrease as needed
                recognized_text = recognizer.recognize_google(audio)

                if "quit dictation" in recognized_text.lower():
                    print("Dictation Ended.")
                    save_dictation_to_file(text)
                    return text
                    #break

                text += recognized_text + " "
                print(recognized_text, end=" ")

            except sr.UnknownValueError:
                nilly = ""
                #print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"Error: {e}")

    engine.stop()

if __name__ == "__main__":
    main()
