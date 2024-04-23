import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from helpers import Config
from huggingface_hub import login


class ChatAPI:
    def __init__(self, cfg: Config, **params) -> None:

        login(cfg.hf_key)

        # Device setup
        device: str = "cuda:0" if cfg.mode == "gpu" else "cpu"
        torch_dtype = torch.float16 if cfg.mode == "gpu" else torch.float32

        # Model and tokenizer setup
        model_id: str = "gorilla-llm/gorilla-openfunctions-v2"  ##LLama tuned for function calling
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True)

        # Move model to device
        model.to(device)

        self.config = cfg
        # Pipeline setup
        self.fPipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1024,
            # batch_size=16,
            torch_dtype=torch_dtype,
            device=device,
        )

        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        self.tModel = AutoModelForCausalLM.from_pretrained(
            "google/gemma-1.1-7b-it",
            quantization_config=quantization_config
        )
        self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-1.1-7b-it")
        # self.tModel.to(device)

    def get_prompt(self, user_query: str, functions: list = []) -> str:
        """
        Generates a conversation prompt based on the user's query and a list of functions.

        Parameters:
        - user_query (str): The user's query.
        - functions (list): A list of functions to include in the prompt.

        Returns:
        - str: The formatted conversation prompt.
        """
        system_message = "You are an AI assistant which can help to generate functions based on query. If passed functions are not sutable try to just response users question or generate a text based on provided context."
        if len(functions) == 0:
            return f"### Instruction: {user_query}\n### Response: "
        functions_string = json.dumps(functions)
        return f"{system_message} \n### Instruction: <<function>> {functions_string}\n<<question>> {user_query}\n### Response: "

    def get_message(self, user_query: str, functions: list = []):
        prompt = self.get_prompt(user_query, functions=functions)
        text = prompt
        if len(functions) != 0:
            resp = self.fPipe(prompt)
            text = resp[0]['generated_text']

        if (text.find("Response:  <<function>>") == -1):
            input_ids = self.tokenizer(prompt, return_tensors="pt").to(self.config.device)
            outputs = self.tModel.generate(**input_ids, max_new_tokens=1000)
            decoded = self.tokenizer.batch_decode(outputs)
            return decoded
        else:
            return text

# Example usage
# query: str = "Call me an Uber ride type \"Plus\" in Berkeley at zipcode 94704 in 10 minutes"
# functions = [
#     {
#         "name": "Uber Carpool",
#         "api_name": "uber.ride",
#         "description": "Find suitable ride for customers given the location, type of ride, and the amount of time the customer is willing to wait as parameters",
#         "parameters":  [
#             {"name": "loc", "description": "Location of the starting place of the Uber ride"},
#             {"name": "type", "enum": ["plus", "comfort", "black"], "description": "Types of Uber ride user is ordering"},
#             {"name": "time", "description": "The amount of time in minutes the customer is willing to wait"}
#         ]
#     }
# ]
