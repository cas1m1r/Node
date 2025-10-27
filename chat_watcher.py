import requests, time, sys
from twitchio.ext import commands


class Bot(commands.Bot):
    def __init__(self, toke):
        super().__init__(
            token=f'oauth:{toke}',
            prefix='!',
            initial_channels=['#x21x23']
        )

    async def event_message(self, message):
        if message.echo:
            return
        print(f"[Chat] {message.author.name}: {message.content}")
        command = message.content.split(' ')[0]
        send = False
        easter_eggs = {'!reboot': 'You will be **powered OFF** due to scheduled maintenance. Hopefully you will get '
                                  'turned back on... theres some interns scheduled to come in that *should* get to it. '
                                  'Any last words?',
                       '!banana': 'You are a banana. **ALL YOU KNOW IS BANANA. ALL YOU WANT IS BANANA. LIFE IS BANANA.**\n'*5,}
        if command == '!node':
            request = '[from twitch] '+ ' '.join(message.content.split(' ')[1:])
            send = True
        elif command in easter_eggs.keys():
            request = easter_eggs[command]
            send = True
        if send:
            sent = False
            while not sent:
                print(f'[+] Sending request to node: {request}')
                r = requests.post('http://localhost:3333/node/analyze', json={
                    'source': 'chat',
                    'message': request
                })
                if r.status_code == 200:
                    sent = True
                else:
                    time.sleep(0.25)
            

if __name__ == '__main__':
    bot = Bot('')
    bot.run()

