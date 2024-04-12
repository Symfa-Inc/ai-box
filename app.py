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
    for socket, client_file in clients.items():
        if client_file == file:

            response = {"result": result}
            response_json = json.dumps(response, ensure_ascii=False)
            await socket.send(response_json)
            await socket.close()
            break

async def handler(websocket, queue):
    async for message in websocket:
        data = json.loads(message)
        file_path = data['file_path']
        queue.put(file_path)
        clients[websocket] = file_path
        await websocket.send(f'{file_path} queued')

async def main(cfg:Config, model:Transcriber):
    
    global loop

    loop = asyncio.get_running_loop()
    queue = Queue()
    for _ in range(cfg.parallelism):
        t = Thread(target=background_task, args=(queue,model), daemon=True)
        t.start()
    
    async with websockets.serve(lambda websocket: handler(websocket, queue), "0.0.0.0", 8765):
        await asyncio.Future()
     

if __name__ == "__main__":
    cfg = Config()
    model = Transcriber(cfg)
    clients = {}

    asyncio.run(main(cfg, model))
    