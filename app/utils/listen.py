import speech_recognition as sr

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from app.utils.speak import speak_text
def listen_and_transcribe():
    r = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("🎙️ Listening for up to 20 seconds. Speak now...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=15)

    try:
        print("🗣️ Recognizing...")
        text = r.recognize_google(audio, language='en-in')
        print(f"🗣️ You said: {text}")
        speak_text(f"You said: {text}")
         # Return the recognized text
         # This can be used in other parts of the application
         # or for further processing.
        return text
    except sr.UnknownValueError:
        return "❌ Sorry, I couldn't understand that."
    except sr.RequestError as e:
        return f"❌ Error with the speech recognition service: {e}"
