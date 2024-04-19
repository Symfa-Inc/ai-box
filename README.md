The AI-Box is an encapsulated solution general AI tasks including:
 - Generative AI. Function calling included `(is in progress)`
   - Proxy to OpenAI
   - The list of OpenSource models: 
     - gorilla-openfunctions-v2
 - Audio processing including
   - Segmentation
   - Diarization
   - Realtime audio stream processing `(is in progress)`

## 1. Building the Docker Image
```shell
docker build -t ai-box:latest .
```

## 2. Running the Docker Container from public repo

To run the Docker container, use the following command:
```shell
docker run -it \
  -v local_path_for_video_files:/usr/src/app/download \
  -p 8765:8765 \
  ghcr.io/symfa-inc/ai-box:latest
```

Mount your local directory  to the container's `/usr/src/app/download` directory, so that the transcriber can access the files for processing.
### 2.1. Docker compose example:

```yaml
version: "3.8"

services:
  aibox:
    image: ghcr.io/symfa-inc/ai-box:latest
    container_name: aibox
    ports:
      - "8765:8765"
    environment:
      SPEAKER: segmentation
      MODE: CPU
      QUALITY: LOW
      PARALLELISM: 1
    volumes:
      - local_path_for_video_files:/usr/src/app/download
```

###  2.2. Options (Environment variables)
You can change parameters of the server to find the optimal performance/quality comprise for you solution with the following parameters:

- `SPEAKER`:  `segmentation` or `diarization`. `diarization` is better but as it can say you who say, what and when. Segmentation is only split audio to segments with different speakers, however it can be better choice for `CPU` processing.
- `MODE`:  `CPU` or `GPU`.
- `QUALITY`: - transcription quality level.
  - `DEBUG` - not acceptable level of quality for most of cases. But can be useful for debug environments. 
  - `LOW` - the optimal level for CPU
  - `MEDIUM`
  - `HIGH`
- `PARALLELISM`: Integer, default `1`. How many files transcriber can process in parallel.


## 3. How to work with the server.

### Request and Response Formats
All requests should follow the JSON format. Below is an example of a request to process a file:
```json
{
  "file_path": "video.mp4",
  "speaker": "diarization", //optional
  "mode": "cpu",            //optional
  "quality": "medium"       //optional
}
```
- `file_path` (required): Specifies the path to the input file.
- `speaker`:  (optional): Specifies the desired processing mode, either `diarization` or `segmentation`.
- `mode` (optional): Specifies the processing mode, either `gpu` or `cpu`.
- `quality`(optional): Specifies the quality of processing, one of `debug`, `low`, `medium`, or `high`.

Responses from  are also in JSON format. Below is an example response to the processing request:
```json
{
  "type": "recording_processed",
  "file_name": "video.wav",
  "data": "{transcriptionText}"
}
```
- `type`: Indicates the status of the processing. It can be "recording_queued" when the file is queued, "recording_processed" when the file is processed successfully, or "recording_errored" if processing failed.
- `file_name`: Specifies the name of the input file. 
- `data`(optional): Contains additional information. If processing is successful, it returns the result of the processing. If processing fails, it returns an error message explaining the failure.


### 3.1 JavaScript
```javascript
const WebSocket = require('ws');

// Connect to the WebSocket server
const ws = new WebSocket('ws://localhost:8765');

ws.on('open', function open() {
    console.log('Connected to server');

    // Send a request to prcess the file. Expectation that the video file 
    // is in the {local_path_for_video_files}
    ws.send(JSON.stringify({"file_path": "video.mp4"}));
});

ws.on('message', function incoming(message) {
    //{"data": "transcriptionText"}.
    console.log('Message from server: %s', message.data);
});

```

### 3.2 Python

```python
import asyncio
import websockets
import json

async def talk():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected to server")
        message = {
            'file_path': "video.mp4",
            'speaker': "segmentation",
            'quality': "medium"
        }
        await websocket.send(json.dumps(message))

        response = await websocket.receive()
        response_json = json.loads(response)
        # {"result": "transcriptionText"}.
        print(f"Message from server: {response_json.data}")

asyncio.run(talk())
```