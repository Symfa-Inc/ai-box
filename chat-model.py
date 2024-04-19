import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from helpers import Config


class ChatAPI:
    def __init__(self, cfg: Config, **params) -> None:
        # Device setup
        device: str = "cuda:0" if Config.mode == "gpu" else "cpu"
        torch_dtype = torch.float16 if Config.mode == "gpu" else torch.float32

        # Model and tokenizer setup
        model_id: str = "gorilla-llm/gorilla-openfunctions-v1" ##LLama tuned for function calling
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True)

        # Move model to device
        model.to(device)

        # Pipeline setup
        self.pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=128,
            batch_size=16,
            torch_dtype=torch_dtype,
            device=device,
        )

    def get_prompt(self, user_query: str, functions: list = []) -> str:
        """
        Generates a conversation prompt based on the user's query and a list of functions.

        Parameters:
        - user_query (str): The user's query.
        - functions (list): A list of functions to include in the prompt.

        Returns:
        - str: The formatted conversation prompt.
        """
        if len(functions) == 0:
            return f"USER: <<question>> {user_query}\nASSISTANT: "
        functions_string = json.dumps(functions)
        return f"USER: <<question>> {user_query} <<function>> {functions_string}\nASSISTANT: "

    def get_message(self, user_query: str, functions: list = []):
        prompt = self.get_prompt(user_query, functions=functions)
        return self.pipe(prompt)

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
