from gtts import gTTS
import pygame
import time
import io 


# Initialize pygame mixer once
pygame.mixer.init()
 
def speak_text(text):
    # Convert text to speech into memory buffer
    tts = gTTS(text, lang='en-in')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    # Save to a temporary in-memory buffer and play
    pygame.mixer.music.load(mp3_fp)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

    return "Speech completed"

# Example usage
speak_text("Hello Anjali! This is an in-memory female voice, no files needed.")
