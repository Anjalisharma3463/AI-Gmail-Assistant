import pyttsx3

# Initialize once globally
engine = pyttsx3.init()

# Configure speech rate and volume
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)

# Find female voice
voices = engine.getProperty('voices')
female_voice = None

for voice in voices:
    if 'female' in voice.name.lower() or 'female' in voice.id.lower():
        female_voice = voice.id
        break

# Fallback: use the second voice if no 'female' found
if not female_voice and len(voices) > 1:
    female_voice = voices[1].id

# Set the selected voice
engine.setProperty('voice', female_voice)

# Speech function
def speak_text(text):
    engine.say(text)
    engine.runAndWait()
    return "Speech completed"
