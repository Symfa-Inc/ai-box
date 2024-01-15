FROM python:3.10.4-slim-bullseye

WORKDIR /usr/src/app
RUN apt-get update -y && apt-get install ffmpeg -y
RUN apt-get install gcc -y
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
RUN apt-get install dnsutils -y
#ENV NVIDIA_VISIBLE_DEVICES=all
COPY docker_init.py ./
RUN HF_TOKEN=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 \
    python ./docker_init.py

COPY . .

CMD [ "python", "./app.py" ]