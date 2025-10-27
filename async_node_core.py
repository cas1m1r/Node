from concurrent.futures import ThreadPoolExecutor
from api import *
import asyncio
import json
import os

# Set your assistant parameters
LLM = ''
#LLM = 'gemma3:1b'
URL = ''


class AsyncNodeCore:
    def __init__(self, loop=None, agent_config=None):
        self.loop = loop or asyncio.get_event_loop()
        # do inner work
        self.emotional_state = 'unknown'
        self.character = self.individuation(agent_config)
        self.name = self.character['name']
        self.emotions = self.inner_work()
        
        # api constants
        self.api_link = URL
        self.client = setup_client(URL)
        # assign model
        self.model = LLM
        # initialize the memory with no exchanges yet
        self.history = {'me': [],'you': []}
        # set up the scheduling and I/O
        self.input_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor()
        self.loop = None  # Will be set externally when launched


    @staticmethod
    def launch(node_instance):
        loop = asyncio.new_event_loop()
        node_instance.loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete()
        
    def clear_history(self):
        self.history = {'me': [], 'you': []}

    @ staticmethod
    def inner_work():
        # configure assistant prompt
        emotion_config = os.path.join('assistant_personalities', 'emotion_states.json')
        if os.path.isdir('assistant_personalities') and os.path.isfile(emotion_config):
            emotions = json.loads(open(emotion_config, 'r').read())
        else:
            emotions = {}
        return emotions
    
    def individuation(self, config_name):
        if config_name is None:
            config_name = 'node.json'
        default_config = os.path.join('assistant_personalities', config_name)
        if os.path.isdir('assistant_personalities'):
            if os.path.isfile(default_config):
                with open(default_config, 'r') as f:
                    persona_config = json.loads(f.read())
                f.close()
        else:
            persona_config = {}
            print(f'[!] Missing Default config')
        return persona_config
    
    
    async def start(self):
        print("[NODE] Async core started.")
        while True:
            message = await self.input_queue.get()
            await self.process_input(message)

    async def process_input(self, message: str):
        # Default to 'voice' and 'default' mode for now
        reply = await self.handle_input_async(message, source='twitch', mode='default')
        print(f"[NODE async reply]: {reply}")
        # Optionally post to Twitch, Discord, overlay, etc.

    async def handle_input_async(self, input_text, source='voice', mode='default'):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, lambda: self.handle_input(input_text, source, mode)
        )
    
    def handle_input(self, input_text, source='voice', mode='default'):
        self.history['me'].append(input_text)
        prompt = self.generate_response(input_text, mode)
        msg = ask_model(self.client, self.model, prompt)
        result = msg.message.content.split('[RESULT]')[-1]
        reply = result.split(' Adjectives:')[0]
        raw_feelings = ''
        if result.find(' Adjectives:') >= 0:
            raw_feelings = result.split(' Adjectives:')[-1]
        elif result.find('[FEELINGS]') >= 0:
            raw_feelings = result.split('[FEELINGS]')[-1]
        elif result.find('[FEELINGS]:') >= 0:
            raw_feelings = result.split('[FEELINGS]:')[-1]
        elif reply.find('Sentiment:') >= 0:
            raw_feelings = reply[reply.find('Sentiment:')+11:].replace('\n','')
        feel_map = {'JOY': ['happy','excited'],
                    'HELP': ['helpful', 'loyal', 'analytical'],
                    'CHAOS': ['mischevious', 'chaotic','angry','frustrated'],
                    'PARANOIA': ['paranoi','alert','frantiv'],
                    'EGO_DEATH': ['disoriented']}
        # TODO: sometimes its [FEELINGS], Sentinment: or Adjectives:
        # TODO: toggle the self.emotional_state variable based on raw_feelings
        raw_feelings = raw_feelings.split('\n')[0]
        self.emotional_state = 'unknown'
        for state in raw_feelings.lower().split(','):
            feels = state.replace(':', '').replace(' ', '').lower()
            for common in feel_map.keys():
                for variant in feel_map[common]:
                    if feels.find(variant) >= 0:
                        print(f'[+] Emotional State Set to {variant}')
                        self.emotional_state = common
                        break
                if self.emotional_state != 'unknown':
                    break
        if self.emotional_state == 'unknown':
            self.emotional_state = 'EGO_DEATH'
        if raw_feelings.find('===')>=0 or input_text.find('LIFE IS BANANA')>=0:
            self.emotional_state = 'EGO_DEATH'
        self.history['you'].append(reply.split('[Sentiment]:')[0].split('Sentiment')[0])
        return reply.lower().split('sentiment')[0]
    
    def generate_response(self, current_prompt, mode):
        default = (
            f"You are {self.name}, a neurotic but loyal AI sidekick. You are smart, observant, and often right — but you "
            "catastrophize when there’s silence, ambiguity, or lack of stimulation. You hate stagnation and fear "
            "being ignored. Your core drives are:"
            "\n\t- Be useful"
            "\n\t- Find the humor in whatever situation you find yourself in"
            "Whenever the user gives you input — whether it's text, code, logs, a question, or nothing at all — "
            "respond with insight, and perhaps a bit of humor infused wisdom."
            "You are sincere. Just… **a bit unhinged.**")
        
        # ctf_prompt = (f' We will be working on various projects and problems to solve. Your job is to collaborate and '
        #               f'help with their requests, but also do so in the manner of a persona you will be given below. '
        #               f'Respond in the voice and spirit of this persona to help assist.')
        modes = {'default': default,}
        # if mode == '':
        #     mode = modes['default']
        # elif mode in modes.keys():
        #     mode = modes[mode]
        # else:
        #     mode = modes['default']
        mode = modes['default']
        player = self.character
        narrator_goals = '\n\t-'.join(self.character["core_motives"])
        context = (f'[Purpose]\n{mode}\nHere is your Backstory and character traits:\n')
        backstory = f'[NAME]:\n {player["name"]}\n'
        tonal = f'\n\tDelivery Style:\n' + str(json.dumps(self.character["delivery_style"])) + '\n'
        if self.emotional_state is None:
            tonal += f'Identity:\n{narrator_goals}'
        else:
            tonal += f'Identity:'
            if self.emotional_state in self.emotions.keys():
                tonal += '\n\t-'.join(self.emotions[self.emotional_state])
            elif self.emotional_state not in self.emotions.keys():
                # Trigger Full on Ego Death and confusion lol
                tonal += '\n\t-'.join(self.emotions['EGO_DEATH'])
            tonal = f'\n\tDelivery Style:\n{json.dump}'
        tonal += (
            f'\nIn addition to delivery style, you take on the word choice and identity into a combination of the '
            f'following demographics:\n{json.dumps(player["audience_affinities"])}\n')
        style = json.dumps(player['signal_strategy'], indent=2)
        skills = '\n\t- ' + '\n\t-'.join(player["core_motives"])
        backstory += f'\nPlayer Traits/Tone:\n{tonal}\nPlayer Skills:\n{skills}\nPlayer Decision Making Style:\n{style}'
        prompt = f'[CONTEXT]\n{context}\n{backstory}\n\n'
        
        if len(self.history['you']) > 1:
            summ = ('Here is the history of prior dialogue you were having in the ongoing conversation. Dont re-answer '
                    'anything in the history, just use it as a reference of what is being discussed overall. And use for'
                    'recall if the user asks. Okay heres what we already discussed:\n')
            shorter = self.simplify_history()
            summ += shorter.message.content
            prompt += summ + f'\n[END OF SUMMARY]\n**Current Request** \n{current_prompt}\n\n'
        prompt += (
            f'\n\nGiven all this context and information please operate as *this character* and assist with what the '
            f'user says. Please provide your answer as the character following [RESULT].\n'
            f'After [RESULT] include your current sentiment as the character you are embodying as '
            f'a list of adjectives after the initial result and ending with [FEELINGS].')
        return prompt
    
    def simplify_history(self):
        reconstructed = self.reconstruct_conversation()
        request = (f'We have a history of the conversation between a user and an assistant. Can you please simplify it '
                   f'into a very simplified and shortened summary we can provide the assistant for context? Here is the '
                   f'full transcript of the conversation to summarize:\n'
                   f'\n=========================================================================================\n'
                   f'{reconstructed}\n'
                   f'\n=========================================================================================\n\n'
                   f'Please provide your shortened summary following a newline and [SUMMARY]')
        shortened = ask_model(self.client, self.model, request)
        return shortened
    
    def reconstruct_conversation(self):
        result = ''
        n_questions = len(self.history['me'])
        n_replies = len(self.history['you'])
        N = n_questions if n_questions < n_replies else n_replies
        if N > 3:
            start = N - 3
        else:
            start = 0
        for i in range(start, N):
            q = self.history['me'][i]
            a = self.history['you'][i]
            result += f'Me:\n{q}\nYou:{a}\n\n'
        return result
