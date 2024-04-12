## Building the Docker Image
docker build -t transcriber
## Running the Docker Container

To run the Docker container, use the following command:

docker run -it -v /local/path/folder_with_videos:usr/src/app/download transcriber

Mount your local directory  to the container's `/usr/src/app/download` directory, so that the transcriber can access the files for processing

## Environment Variables

- `SPEAKER`:  `segmentation` or `diarization`.
- `MODE`:  `CPU` or `GPU`.
- `QUALITY`: `DEBUG`, `LOW`, `MEDIUM`, `HIGH`. 
- `PARALLELISM`: Integer, default `1`.

Websocket runs on  8765 port.

Example request.
{"file_path":"/usr/src/app/download/video.mp4"}. 

Returns JSON with a transcription 
{"result": transcription}.
