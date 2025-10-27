from flask import Flask, request, jsonify, render_template, redirect,render_template_string
from dotenv import load_dotenv
from chat_watcher import Bot
from queue import Queue
import multiprocessing
import numpy as np
import threading
import asyncio
import time
import json
import api
import os


global MUTE
global TWITCH
global T0
global DT
global twitch_watcher

import asyncio
import async_node_core as node_core

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
assistant = node_core.AsyncNodeCore(loop=loop,agent_config='mobius.json')
# Start assistant's event loop in a thread
def run_async_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=run_async_loop, daemon=True)
loop_thread.start()

T0 = time.time()
DEBUG = True
MUTE = False
TWITCH = False
SETTINGS = {False: 0.6,
            True: 0.55}
TIMEOUT = 60*5
app = Flask(__name__)
from personas_api import bp as personas_bp
app.register_blueprint(personas_bp)
PERSONA_DIR = "./assistant_personalities"


@app.route("/personas")
def index():
    persona_files = [f for f in os.listdir(PERSONA_DIR) if f.endswith(".json")]
    return render_template_string("""
        <style>
         body{background:#0f0f0f;color:#e6fff6;font-family:system-ui;margin:12px}
         .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
         select,button,input,textarea{font-size:16px;padding:10px;border-radius:10px;border:1px solid #2b3a3a;background:#12181f;color:#dff}
         textarea{width:100%;height:60vh}
         .ok{color:#8affc1} .err{color:#ff9b9b}
        </style>
        <h2>Persona Editor</h2>
        <select id="personaSelect">
            {% for f in persona_files %}
            <option value="{{f}}">{{f}}</option>
            {% endfor %}
        </select>
        <br><br>
        <textarea id="personaText" style="width: 80%; height: 400px;"></textarea><br>
        <button onclick="savePersona()">Save</button>
        <button onclick="changePersona()">Switch to this Model</button>
        <script>

        async function loadPersona(name) {
            let res = await fetch('/get_persona/' + name);
            let text = await res.text();
            document.getElementById('personaText').value = text;
        }

        document.getElementById('personaSelect').addEventListener('change', function() {
            loadPersona(this.value);
        });

        async function savePersona() {
            let name = document.getElementById('personaSelect').value;
            let content = document.getElementById('personaText').value;
            let res = await fetch('/save_persona/' + name, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({"content": content})
            });
            alert(await res.text());
        }
        async function changePersona(){
          let name = document.getElementById('personaSelect').value;
          console.log(name);
          const res = await fetch(`/switch-assistants/`+ name, {
            methods: 'GET',
            headers: {'Content-Type': 'application/json'}
          });
          await res.text();
        }

        // Load first persona on page load
        window.onload = () => {
            loadPersona(document.getElementById('personaSelect').value);
        }
        </script>
    """, persona_files=persona_files)



@app.route('/switch-assistants/<config>')
def change_assistant(config):
    global assistant
    asyncio.set_event_loop(loop)
    assistant = node_core.AsyncNodeCore(loop=loop, agent_config=config)
    return redirect('/')

@app.route("/get_persona/<name>")
def get_persona(name):
    path = os.path.join(PERSONA_DIR, name)
    if not os.path.exists(path):
        return "Not found", 404
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/save_persona/<name>", methods=["POST"])
def save_persona(name):
    path = os.path.join(PERSONA_DIR, name)
    data = request.json
    content = data.get("content", "")
    try:
        json.loads(content)  # validate JSON
        # make backup
        os.rename(path, path + ".bak")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "Saved successfully"
    except Exception as e:
        return f"Error saving: {e}", 400


@app.route('/node/analyze', methods=['POST'])
def analyze():
    global assistant, loop
    if request.is_json:
        input_text = request.json.get('message', '')
    else:
        input_text = request.form['message']
    emotions = 'default'
    # Call your internal NODE engine here
    print(f'[-] Asking "{input_text}"')
    assistant.loop = loop
    response = asyncio.run_coroutine_threadsafe(
        assistant.handle_input_async(input_text, source='web',mode=emotions),
        assistant.loop
    ).result()
    print(f'[-] Got reply to form submitted question')
    
    # Todo: put the reply back into the page
    # return render_template('chat.html',form={'message': ''},texts=result)
    return redirect('/')


@app.route('/')
def home():
    global MUTE
    global DT
    volume = {False: 'speaker.png',
              True: 'speaker2.png'}
    twitch_state = {False:'',
                    True:'twitch.png'}
    model_list = api.list_models(assistant.client)
    volume_icon = volume[MUTE]
    DT = time.time() - T0
    # periodically run a task to simplify the conversation history to be refined for the prompt to make more
    if round(DT) >= TIMEOUT:
        assistant.simplify_history()
        DT = 0
    return render_template('chat.html', form={'message': 'Ask a question....'},
                           texts=assistant.history['you'], models=model_list, volume_state=volume_icon, has_twitch=TWITCH)

# view-models
@app.route('/view-models')
def list_models():
    model_list = api.list_models(assistant.client)
    current = assistant.model
    return render_template('models.html',models=model_list, current_model=current)


@app.route('/pull-model', methods=['POST'])
def get_model():
    model_to_download = request.form['model_to_download']
    print(f'[o] Downloading model {model_to_download}')
    api.download_model(assistant.client,model_to_download)
    return redirect('/view-models')


@app.route('/download-model')
def download_model_form():
    return render_template('download.html')

@app.route('/enable-twitch-interactions')
def start_twitch_integraton():
    load_dotenv()
    app_id = os.environ['AUTH']
    oauth_uri = f'https://id.twitch.tv/oauth2/authorize?response_type=token&client_id={app_id}&redirect_uri=https://id.twitch.tv&scope=chat%3Aread+chat%3Aedit'
    return render_template('enable_bot.html', oauth=oauth_uri)
    
    
@app.route('/finish-auth',methods=['POST'])
def integrate_twitch():
    global TWITCH
    global twitch_watcher
    # IRC Server Settings (Example)
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = '#!'
    auth = request.form['token']
    token = f'{auth}'
    channel = f'#x21x23'
    os.system(f'start python chat_watcher.py {token}')
    print(f'[+] Starting Twitch Listener')
    # maybe start bot in a diff thread?
    TWITCH = True
    return redirect('/')
    
@app.route('/reset-node')
def reset_node_history():
    assistant.clear_history()
    print(f'[+] Node history cleared')
    return redirect('/')
    
# Assets
@app.route('/static/<file>')
def serve_static(file):
    fname = os.path.join('assets',file)
    if os.path.isfile(fname):
        with open(fname,'rb') as f:
            data = f.read()
        f.close()
        return data
    else:
        '<h1>unknown</h1>'





if __name__ == "__main__":
    
    app.run('127.0.0.1',port=3333, debug=False)

