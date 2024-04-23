import asyncio
import json
import jsonschema.exceptions
import websockets
from queue import Queue
from threading import Thread
import time
import pathlib
import jsonschema

from helpers import Config, ResponseType
from model import Transcriber
from chat_model import ChatAPI

def background_task(queue):
    while True:
        if queue.empty() == False:
            file, model = queue.get()
            try:
                result = model.run(file)
                type = ResponseType.recording_processed.name
            except Exception as ex:
                result = str(ex)
                type = ResponseType.recording_errored.name
            finally:
                del model

                file_name = pathlib.Path(file).name
                response = {
                        "type": type,
                        "file_name": file_name,
                        "data": result
                }
                response_json = json.dumps(response, ensure_ascii=False)
                asyncio.run_coroutine_threadsafe(send_result(file, response_json), loop)
            
        time.sleep(1) 


async def send_result(file, result):
    for client_id, (socket, client_files) in clients.items():
        if client_id == socket.id:
            if file in client_files:
                await socket.send(result)
                client_files.remove(file)
            if not client_files:
                await socket.close()
                del clients[client_id]
                break

async def handler(websocket, queue):

    fileUploadSchema = {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
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

        data = json.loads(message)

        if data.operation == "gpt_message":
            chatApi = ChatAPI(cfg)
            message = chatApi.get_message(data.query)
            response = {
                "type": ResponseType.gpt_message.name,
                "response": message
            }
            response_json = json.dumps(response, ensure_ascii=False)
            await websocket.send(response_json)
        elif data.operation == "transcript_file":
            try:
                jsonschema.validate(instance=data, schema=fileUploadSchema)
            except jsonschema.exceptions.ValidationError as ex:
                await websocket.send(f"Bad request: {ex.message}")
                # await websocket.close()
            except Exception as ex:
                await websocket.send(f"Bad request: {ex}")
                # await websocket.close()
            else:

                file_path = f'/usr/src/app/download/{data["file_path"]}'
                model = Transcriber(cfg, **data)
                queue.put((file_path, model))

                client_id = websocket.id
                clients.setdefault(client_id, (websocket, []))
                clients[client_id][1].append(file_path)

                response = {
                    "type": ResponseType.recording_queued.name,
                    "file_name": data["file_path"]
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
    