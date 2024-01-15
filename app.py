import os

from azure_processor import download_all_files_from_blob
from chunks_based_on_diarization_txt import processAllMp4Files

download_all_files_from_blob()

processAllMp4Files()

