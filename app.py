import asyncio
import json
import jsonschema.exceptions
import websockets
from queue import Queue
from threading import Thread
import time
import pathlib
import jsonschema

from config import Config
from model import Transcriber


def background_task(queue):
    while True:
        if queue.empty() == False:
            file, model = queue.get()
            result = model.run(file)
            del model
            asyncio.run_coroutine_threadsafe(send_result(file, result), loop)
            
        time.sleep(1) 


async def send_result(file, result):
    for client_id, (socket, client_files) in clients.items():
        if client_id == socket.id:
            if file in client_files:
                file_name = pathlib.Path(file).name

                response = {
                    "file_name": file_name,
                    "result": result
                }
                response_json = json.dumps(response, ensure_ascii=False)
                await socket.send(response_json)
                client_files.remove(file)
            if not client_files:
                await socket.close()
                del clients[client_id]
                break

async def handler(websocket, queue):

    schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "speaker": {
                "type": "string",
                "enum": ["diarization", "segmentation"]
            },
            "mode": {
                "type": "string",
                "enum": ["cpu", "gpu"]
            },
            "quality": {
                "type": "string",
                "enum": ["debug", "low", "medium", "high"]
            }
        },
        "required": ["file_path"]
    }

    async for message in websocket:
        
        try:
            data = json.loads(message)
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as ex:
            await websocket.send(f"Bad request: {ex.message}")
            await websocket.close()
        except Exception as ex:
            await websocket.send(f"Bad request: {ex}")
            await websocket.close()
        else:

            file_path = f'/usr/src/app/download/{data["file_path"]}'

            model = Transcriber(cfg, **data)
            queue.put((file_path, model))

            client_id = websocket.id
            clients.setdefault(client_id, (websocket, []))
            clients[client_id][1].append(file_path)

            response = {
                "file_name": data["file_path"],
                "result": "File queued"
            }
            response_json = json.dumps(response, ensure_ascii=False)
            await websocket.send(response_json)

async def main(cfg:Config):
    
    global loop

    loop = asyncio.get_running_loop()
    queue = Queue()
    for _ in range(cfg.parallelism):
        t = Thread(target=background_task, args=(queue,), daemon=True)
        t.start()
    
    async with websockets.serve(lambda websocket: handler(websocket, queue), cfg.host, cfg.port):
        await asyncio.Future()
     

if __name__ == "__main__":
    cfg = Config()
    clients = {}

    asyncio.run(main(cfg))
    