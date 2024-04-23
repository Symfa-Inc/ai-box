from chat_model import ChatAPI
from helpers import Config

cfg = Config()
chatApi = ChatAPI(cfg)

functions = [
    {
        "name": "Uber Carpool",
        "api_name": "uber.ride",
        "description": "Find suitable ride for customers given the location, type of ride, and the amount of time the customer is willing to wait as parameters",
        "parameters":  [
            {"name": "loc",  "description": "Location of the starting place of the Uber ride", "type": "string", },
            {"name": "type", "enum": ["plus", "comfort", "black"], "description": "Types of Uber ride user is ordering"},
            {"name": "time", "description": "The amount of time in minutes the customer is willing to wait", "type": "string"}
        ]
    }
]
query = "Call me an Uber ride type \"Plus\" in Berkeley at zipcode 94704 in 10 minutes"


message = chatApi.get_message(query, functions)

print(message)