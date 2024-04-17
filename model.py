import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline, Model
from pyannote.audio.pipelines import VoiceActivityDetection, OverlappedSpeechDetection
from pydub import AudioSegment
import os
import pathlib
import glob
import re
import torchaudio
from moviepy.editor import VideoFileClip
from recordclass import recordclass
import shutil

from helpers import Config

class BaseTask():

    def __init__(self, quality, device) -> None:

        if quality == "debug":
            self.model_size = "tiny"
        elif quality == "low":
            self.model_size = "small"
        elif quality == "medium":
            self.model_size = "medium"
        else:
            self.model_size = "large-v3"

        self.dtype = "default" if quality == "high" else "int8"
        self.condition_on_previous_text = True if quality == "high" else False
        
        if quality == "high":
            self.best_of = 5
            self.beam_size = 5 
        elif quality == "debug":
            self.best_of = 1
            self.beam_size = 1
        else:
            self.best_of = 2 
            self.beam_size = 3 
        
        self.whisper_model = WhisperModel(model_size_or_path=self.model_size, device=device, compute_type=self.dtype)

    def extract_audio_from_video(self, video_path, wav_path):
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(wav_path, codec='pcm_s16le', logger=None)
        video.close()

        return wav_path

    def ms_to_time(self, ms):
        hours = ms // (1000 * 60 * 60)
        minutes = (ms // (1000 * 60)) % 60
        seconds = (ms // 1000) % 60

        return f"{hours:02}hours {minutes:02}min {seconds:02}sec"
    
    def millisec(self, timeStr):
        spl = timeStr.split(":")
        s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2])) * 1000)

        return s

    def transcribe_with_whisper(self,file_path):
        if file_path is not None:
            audio = file_path
        else:
            return "You must provide a mic recording or a file"
        
        segments, _ = self.whisper_model.transcribe(
            audio=audio, 
            task="transcribe", 
            chunk_length=30, 
            max_new_tokens=128, 
            without_timestamps=True, 
            condition_on_previous_text=self.condition_on_previous_text,
            best_of=self.best_of, 
            beam_size=self.beam_size)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text
        return full_text
    
    def split_audio(self,file_path, list, task):
        audio = AudioSegment.from_file(file_path)       
        parts = []
        if task == "diarization":
            for start, end, speaker in list:
                part = audio[start:end]
                parts.append([part, speaker, self.ms_to_time(start)])  

            return parts
        else:
            for start, end in list:
                part = audio[start:end]
                parts.append([part, self.ms_to_time(start)])

            return parts
    
    def process_audio(self, file_path, pipeline, output_dir):

        if not pathlib.Path(file_path).is_file():
            raise FileNotFoundError("Invalid path or file does not exists")
        
        file_name = pathlib.Path(file_path).stem
       
        chunks_path = f"{output_dir}/{file_name}/chunks"
        wav_path = f"{output_dir}/{file_name}/{file_name}.wav"

        os.makedirs(chunks_path, exist_ok=True)

        self.extract_audio_from_video(file_path, wav_path)
        waveform, sample_rate = torchaudio.load(wav_path)

        results = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        task = "segmentation" if isinstance(pipeline, VoiceActivityDetection) else "diarization"
        if task == "segmentation":
            Tran = recordclass('Tran', 'start end')
        else:
            Tran = recordclass('Tran', 'start end speaker')
        
        segments = []

        for line in str(results).splitlines():
            start, end = tuple(re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=line))
            start = self.millisec(start)

            if start > 200:
                start = start - 200

            end = self.millisec(end)
            if task == "segmentation":
                segments.append(Tran(start, end))
            else:
                lex = re.findall('SPEAKER_\d+', string=line)
                if len(segments) > 0 and (segments[-1].speaker == lex[0] or end - start < 1000):
                    segments[-1].end = end
                else:
                    segments.append(Tran(start, end, speaker=lex[0]))

        chunks = self.split_audio(wav_path, segments, task)

        for i, chunk in enumerate(chunks):
            chunk_name = f"{chunks_path}/{i:04}-{chunk[1]}-({chunk[2]}).wav" if task == "diarization" else f"{chunks_path}/{i:04}-({chunk[1]}).wav"
            chunk[0].export(chunk_name, format="wav")
        
        file_paths = glob.glob(f"{chunks_path}/*.wav")
        file_paths = sorted(file_paths)
        full_transcription = ""
        
        for file_path in file_paths:
            if task == "diarization":
                fileNamePattern = re.compile('(SPEAKER_\d+)-\((.+)\)\.wav')
                match = fileNamePattern.search(file_path)
                speaker = match.group(1)
                timecode = match.group(2)
                transcription = self.transcribe_with_whisper(file_path)
                formatted_transcription = f"{speaker}, time: {timecode}: {transcription}\\n"
            else:
                fileNamePattern = re.compile('\((.+)\)\.wav')
                match = fileNamePattern.search(file_path)
                timecode = match.group(1)
                transcription = self.transcribe_with_whisper(file_path)
                formatted_transcription = f"time: {timecode}: {transcription}\\n"
            
            full_transcription += formatted_transcription

        shutil.rmtree(f"{output_dir}/{file_name}/")
        return full_transcription


class Diarization(BaseTask):
    def __init__(self, cfg: Config, quality, device) -> None:

        super().__init__(quality, device)

        self.pipe_name = "pyannote/speaker-diarization-3.1" if quality == "high" else "G-Root/speaker-diarization-optimized"

        self.pipeline = Pipeline.from_pretrained(checkpoint_path=self.pipe_name, use_auth_token=cfg.hf_key)
        self.pipeline.to(torch.device(device))

    def process(self, file_path):
        return self.process_audio(file_path, self.pipeline, "processed")

  
class Segmentation(BaseTask):
    def __init__(self, cfg: Config, quality, device) -> None:
        super().__init__(quality, device)
        self.model = Model.from_pretrained("pyannote/segmentation", use_auth_token=cfg.hf_key)
        self.hyper_params = {
          # onset/offset activation thresholds
          "onset": 0.767, "offset": 0.713,
          # remove speech regions shorter than that many seconds.
          "min_duration_on": 0.182,
          # fill non-speech regions shorter than that many seconds.
          "min_duration_off": 0.501
        }
        self.pipeline = VoiceActivityDetection(segmentation=self.model)
        self.pipeline.instantiate(self.hyper_params)
        self.pipeline.to(torch.device(device))

    def process(self,file_path):
        return self.process_audio(file_path, self.pipeline, "processed")


class Transcriber():
    def __init__(self, cfg: Config, **params) -> None:
        
        self.speaker = params.get("speaker", cfg.speaker)
        self.mode = params.get("mode", cfg.mode)
        self.device = "cuda" if self.mode == "gpu" else "cpu"
        self.quality = params.get("quality", cfg.quality)
        
        if self.speaker == "segmentation":
            self.model = Segmentation(cfg, self.quality, self.device)
        else:
            self.model = Diarization(cfg, self.quality, self.device)

    def run(self, file_path):
        return self.model.process(file_path)