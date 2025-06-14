import speech_recognition as sr

def listen_and_transcribe():
    r = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("🎙️ Listening... Speak now.")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)

    try:
        print("🗣️ Recognizing...")
        text = r.recognize_google(audio, language='en-in')
        print(f"🗣️ You said: {text}")
        return text
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError as e:
        return f"Error with the speech recognition service: {e}"
