import asyncio
import json
import websockets
from queue import Queue
from threading import Thread
import time

from config import Config
from model import Transcriber


def background_task(queue, model:Transcriber):
    while True:
        if queue.empty() == False:
            file = queue.get()
            result = model.run(file)
            
            asyncio.run_coroutine_threadsafe(send_result(file, result), loop)
            
        time.sleep(1) 


async def send_result(file, result):
    for client_id, (socket, client_files) in clients.items():
        if client_id == socket.id:
            if file in client_files:
                response = {"result": result}
                response_json = json.dumps(response, ensure_ascii=False)
                await socket.send(response_json)
                client_files.remove(file)
            if not client_files:
                await socket.close()
                del clients[client_id]
                break

async def handler(websocket, queue):
    async for message in websocket:
        data = json.loads(message)
        file_path = data['file_path']
        queue.put(file_path)

        client_id = websocket.id
        clients.setdefault(client_id, (websocket, []))
        clients[client_id][1].append(file_path)

        await websocket.send(f'{file_path} queued')

async def main(cfg:Config, model:Transcriber):
    
    global loop

    loop = asyncio.get_running_loop()
    queue = Queue()
    for _ in range(cfg.parallelism):
        t = Thread(target=background_task, args=(queue,model), daemon=True)
        t.start()
    
    async with websockets.serve(lambda websocket: handler(websocket, queue), cfg.host, cfg.port):
        await asyncio.Future()
     

if __name__ == "__main__":
    cfg = Config()
    model = Transcriber(cfg)
    clients = {}

    asyncio.run(main(cfg, model))
    