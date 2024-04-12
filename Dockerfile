FROM pytorch/pytorch:2.1.1-cuda12.1-cudnn8-runtime

WORKDIR /usr/src/app
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install ffmpeg libavcodec-extra git -y
RUN apt-get install libpq-dev libglib2.0-0 build-essential -y
RUN apt-get install gcc -y


RUN pip install -U pip setuptools
RUN pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

COPY . .
RUN pip install -r requirements.txt


RUN mkdir /.config && chmod a+rwx -R /.config
RUN mkdir /.cache || chmod a+rwx -R /.cache
RUN chmod a+rwx -R /usr/src/app/download
RUN chmod a+rwx -R /usr/src/app/processed

EXPOSE 8765

RUN ["sh", "-c", "export LD_LIBRARY_PATH=`python -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + \":\" + os.path.dirname(nvidia.cudnn.lib.__file__))'`"]



ENTRYPOINT  [ "python", "app.py" ]