from ollama import Client, AsyncClient, ChatResponse
import base64


def setup_client(host):
    return Client(host=f'http://{host}:11434', headers={'Content-Type': 'application/json'})


def list_models(client):
    model_data = client.list()
    models = []
    for m in model_data.models:
        models.append(m.model)
    return models


def ask_model(client, model, prompt):
    response = client.chat(model=model, messages=[
      {
        'role': 'user',
        'content': prompt,
      },
    ])
    return response


async def async_ask_model(host, model, prompt):
    client = AsyncClient(host=f'http://{host}:11434', headers={'Content-Type': 'application/json'})
    try:
        response: ChatResponse = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        print(response.message["content"])
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        pass


def delete_model(client, model):
    client.delete(model)
    print(f'[+] Deleting {model}')


def download_model(client, model):
    print(f'[+] Pulling model: {model}')
    client.pull(model)
