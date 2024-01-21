import re
import os
import glob
import time
from recordclass import recordclass
from pydub import AudioSegment
from moviepy.editor import VideoFileClip

import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

w_model_id = "openai/whisper-large-v3"

w_model = AutoModelForSpeechSeq2Seq.from_pretrained(
    w_model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)
# model = model.to_bettertransformer()
w_model.to(device)

processor = AutoProcessor.from_pretrained(w_model_id)

w_pipe = pipeline(
    "automatic-speech-recognition",
    model=w_model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=128,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,
)

from pyannote.audio import Pipeline

read_key = os.environ.get('HF_TOKEN', None)
print(f"HF_TOKEN: {read_key}")
pyannote_pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-3.1',
    use_auth_token=read_key)
# send pipeline to GPU (when available)
pyannote_pipeline.to(torch.device("cuda"))

def transcribe_with_whisper(file_path):
    if file_path is not None:
        audio = file_path
    else:
        return "You must provide a mic recording or a file"
    result = w_pipe(audio, generate_kwargs={"task": "transcribe"})
    return result["text"]

def extract_audio_from_video(video_path, audio_path):
    # Извлечение аудиодорожки из видео
    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path, codec='libmp3lame')#'pcm_s32le') -wav
    video.close()
    return audio_path

def ms_to_time(ms):
    hours = ms // (1000 * 60 * 60)
    minutes = (ms // (1000 * 60)) % 60
    seconds = (ms // 1000) % 60
    milliseconds = ms % 1000

    return f"{hours:02}hours {minutes:02}min {seconds:02}sec"
def millisec(timeStr):
  spl = timeStr.split(":")
  s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
  return s

def split_audio(file_path, list):
    # Загрузка аудиофайла
    audio = AudioSegment.from_file(file_path)

    # Деление аудиофайла на части
    parts = []
    for start, end, speaker  in list:
      part = audio[start:end]
      parts.append([part, speaker, ms_to_time(start)])

    return parts

def processAllMp4Files():
    # Specify the directory you want to list
    folder_path = 'download'

    # List all .mp4 files in this folder
    for file in os.listdir(folder_path):
        if file.endswith('.mp4'):
            file_name_without_extension, _ = os.path.splitext(file)
            file_path = os.path.join(folder_path, file)

            chunks_path = f"processed/{file_name_without_extension}/chunks"
            mp3_path = f"processed/{file_name_without_extension}.mp3"
            os.makedirs(chunks_path, exist_ok=True)

            extract_audio_from_video(file_path, mp3_path)
            print(f"audio extracted")
            waveform, sample_rate = torchaudio.load(mp3_path)

            start_time = time.time()
            dz = pyannote_pipeline({"waveform": waveform, "sample_rate": sample_rate})
            dz = f"{dz}".splitlines()
            end_time = time.time()  # End time
            processing_time = end_time - start_time  # Calculate processing time

            print(f"pyannote_pipeline completed. Processing Time: {processing_time:.2f} seconds\n")
            dzList = []
            Tran = recordclass('Tran', 'start end speaker')

            for l in dz:
              # print(f"checking dz: {l}")
              start, end =  tuple(re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=l))

              start = millisec(start)
              if start > 200:
                start = start - 200

              end = millisec(end)
              lex = re.findall('SPEAKER_\d+', string=l)
              if len(dzList) > 0 and (dzList[-1].speaker == lex[0] or end - start < 1000):
                  dzList[-1].end = end
              else:
                dzList.append(Tran(start, end, speaker = lex[0]))

            print(f"split_audio started")
            chunks = split_audio(mp3_path, dzList)
            print(f"chunks are ready")

            for i, chunk in enumerate(chunks):
                chunk_name = f"processed/{file_name_without_extension}/chunks/{i:04}-{chunk[1]}-({chunk[2]}).mp3"
                chunk[0].export(chunk_name, format="mp3")
                print(f"Сохранен отрезок: {chunk_name}")

            # Соберите все файлы по маске
            file_paths = glob.glob(f"processed/{file_name_without_extension}/chunks/????-SPEAKER_??-*.mp3")

            # Файл для сохранения результатов
            result_file = f"processed/{file_name_without_extension}/transcriptions.txt"

            with open(result_file, "w", encoding='utf-8') as output_file:
                for file_path in file_paths:
                    fileNamePattern = re.compile('(SPEAKER_\d+)-\((.+)\)\.mp3')
                    match = fileNamePattern.search(file_path)
                    speaker = match.group(1)
                    timecode = match.group(2)
                    transcription = transcribe_with_whisper(file_path)
                    output_file.write(f"{speaker}, time: {timecode}: {transcription}\n")
                    print(f"{speaker}, time: {timecode}: {transcription[:30]}...")

            print(f"Транскрипции сохранены в {result_file}")