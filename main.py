from characters import ArchetypeCharacter, load_personas
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from api import *
import keyboard
import pyttsx3
import time
import json
import os

SAMPLERATE = 16000
CHANNELS = 1
MODEL = whisper.load_model("base")

engine = pyttsx3.init(driverName='sapi5')
engine.setProperty("volume", 0.66)

# Set your assistant parameters
LLM = ''
URL = ''


class Assistant:
    def __init__(self, persona_config: ArchetypeCharacter):
        # setup the assistant prompt
        self.character = persona_config
        # Build memory?
        self.history = []

    def show_history(self):
        print(json.dumps(self.history, indent=2))

    def ask(self, question, client):
        assistant_prompt = self.build_assistant_prompt(question)
        # ask LLM with improved prompt
        character_reply = ask_model(client, LLM, assistant_prompt).message.content.split('[RESULT]\n')[-1].split('[THOUGHTS]')[0]
        character_ideas = character_reply.split('[THOUGHTS]')[-1]
        self.history.append({'Question': question, "Reply": character_reply, "Thoughts": character_ideas})
        return character_reply.replace('*','')

    def run(self):
        print("🔁 Assistant ready. Hold 'r' to speak.")
        client = setup_client(URL)
        download_model(client, LLM)
        while True:
            try:
                filename = record_while_key_pressed('r')
                print("🧠 Transcribing...")
                result = MODEL.transcribe(filename)
                print(f"💬 You said: '{result['text']}' (press BACKSPACE to cancel)")
                time.sleep(2.5)
                if keyboard.is_pressed('backspace'):
                    print("❌ Skipped by user.")
                    continue
                if result == '':
                    print("❌ Ignoring Empty transcription")
                    continue
                time.sleep(0.5)
                character_reply = self.ask(result['text'], client)
                engine.say(character_reply)
                engine.runAndWait()
            
            except KeyboardInterrupt:
                print("\n👋 Exiting assistant.")
                break
    
    def build_assistant_prompt(self, current_prompt):
        player = self.character
        narrator_goals = '\n\t-'.join(self.character["core_motives"])
        context = (
            f'You are a helpful assistant working in collaboration with a team of developers. We will be working on various'
            f'projects and problems to solve. Your job is to collaborate and help with their requests, but also do so in'
            f' the manner of a persona you will be given below. Respond in the voice and spirit of this persona to help '
            f'assist. Here is your Backstory and character traits:\n')
        backstory = f'[NAME]:\n {player["name"]}\n'
        tonal = f'\n\tDelivery Style:\n{json.dumps(player["delivery_style"], indent=2)}\n'
        tonal += (
            f'\nIn addition to delivery style, you take on the word choice and identity into a combination of the '
            f'following demographics:\n{json.dumps(player["audience_affinities"])}\n')
        style = json.dumps(player['signal_strategy'], indent=2)
        skills = '\n\t- ' + '\n\t-'.join(player["core_motives"])
        backstory += f'\nPlayer Traits/Tone:\n{tonal}\nPlayer Skills:\n{skills}\nPlayer Decision Making Style:\n{style}'
        prompt = f'[CONTEXT]\n{context}\n{backstory}**Current Request** \n{current_prompt}\n\n'
        summ = ''
        if len(self.history) > 1:
            summ = (
                'Here is the history of prior questions you were asked to give context to the ongoing conversation you '
                'are in.[HISTORY]\n')
            for entry in self.history[-5:]:
                summ += f'\nQuestion: {entry["Question"]["text"]}\nYou Replied:\n{entry["Reply"]}\n'
            prompt += summ + '\n========================================================\nEND OF HISTORY\n'
        
        prompt += (
            f'\n\nGiven all this context and information please operate as *this character* and assist with the request '
            f'above. But please also be concise in your answers. If the question asked is very complicated of course you'
            f'can elaborate, but dont always reply with long rambling answers mix up the length of your replies. Sometimes '
            f'what you *dont* say can be as important as what you do. '
            f'Please provide your answer as the character following [RESULT].\n'
            f'If the character also has an inner dialogue left unspoken please include that as well after [THOUGHTS].')
        return prompt


def record_while_key_pressed(key='?'):
    print(f"⌛ Waiting for you to press [{key}] to speak...")

    # Wait for key press
    keyboard.wait(key)
    print("🎙️ Recording... (release to stop)")
    recording = []

    # Start recording chunks while key is held down
    with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16') as stream:
        while keyboard.is_pressed(key):
            audio_chunk, _ = stream.read(1024)
            recording.append(audio_chunk)
        print("🛑 Stopped recording.")

    # Concatenate chunks and save
    audio_np = np.concatenate(recording, axis=0)
    sf.write("output.wav", audio_np, SAMPLERATE)
    return "output.wav"


def main():
    character_folder = os.path.join(os.getcwd(),'assistant_personalities')
    persona_config_file = os.path.join(character_folder, 'node.json')
    assistant_persona = load_personas(character_folder)['node']
    llm_buddy = Assistant(assistant_persona)
    llm_buddy.run()


if __name__ == "__main__":
    main()