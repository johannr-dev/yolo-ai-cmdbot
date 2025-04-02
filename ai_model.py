# MIT License
# Copyright (c) 2023-2024 wunderwuzzi23
# Greetings from Seattle! 

from abc import ABC, abstractmethod
from openai import OpenAI
from groq import Groq
from ollama import Client
from openai import AzureOpenAI 
from anthropic import Anthropic
import os
import boto3
import json

class AIModel(ABC):
    @abstractmethod
    def chat(self, model, messages):
        pass

    @abstractmethod
    def moderate(self, message):
        pass

    @staticmethod
    def get_model_client(config):
        api_provider=config["api"]

        if api_provider == "" or api_provider==None:
            api_provider = "groq"
        
        if api_provider == "groq":
            return GroqModel(api_key=os.environ.get("GROQ_API_KEY"))
        
        elif api_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:  
                api_key=config["openai_api_key"]       
            if not api_key:  #If statement to avoid "invalid filepath" error
                home_path = os.path.expanduser("~")   
                api_key=open(os.path.join(home_path,".openai.apikey"), "r").readline().strip()
                api_key = api_key

            return OpenAIModel(api_key=api_key)
        
        elif api_provider == "azure":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            if not api_key:  
                api_key=config["azure_openai_api_key"]
            if not api_key: 
                home_path = os.path.expanduser("~")   
                api_key=open(os.path.join(home_path,".azureopenai.apikey"), "r").readline().strip()

            return AzureOpenAIModel(
                    api_key=api_key,
                    azure_endpoint=config["azure_endpoint"], 
                    api_version=config["azure_api_version"])
        
        elif api_provider == "ollama":
            ollama_api   = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
            #ollama_model = os.environ.get("OLLAMA_MODEL", "llama3-8b-8192")
            return OllamaModel(ollama_api)

        if api_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key: 
                api_key=config["anthropic_api_key"]
            return AnthropicModel(api_key=api_key)
        
        elif api_provider == "bedrock":
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            if not aws_access_key:
                aws_access_key = config.get("aws_access_key_id", "")
            if not aws_secret_key:
                aws_secret_key = config.get("aws_secret_access_key", "")
            
            aws_region = config.get("aws_region", "us-east-1")
            aws_profile = config.get("aws_profile", "default")
            
            return BedrockModel(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                region=aws_region,
                profile_name=aws_profile
            )
        else:
            raise ValueError(f"Invalid AI model provider: {api_provider}")

class GroqModel(AIModel):
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def chat(self, messages, model, temperature, max_tokens):
        resp = self.client.chat.completions.create(model=model, 
                                                   messages=messages, 
                                                   temperature=temperature, 
                                                   max_tokens=max_tokens)
        return resp.choices[0].message.content
    
    def moderate(self, message):
        pass

class OpenAIModel(AIModel):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def chat(self, messages, model, temperature, max_tokens):
        resp = self.client.chat.completions.create(model=model, 
                                                   messages=messages, 
                                                   temperature=temperature,
                                                   max_tokens=max_tokens)
        
        return resp.choices[0].message.content
    
    def moderate(self, message):
        return self.client.moderations.create(input=message)

class OllamaModel(AIModel):
    def __init__(self, host):
        self.client = Client(host=host)
    
    def chat(self, messages, model, temperature, max_tokens):
        resp = self.client.chat(model=model, 
                                messages=messages)
        return resp["message"]["content"]
    
    def moderate(self, message):
        pass


class AzureOpenAIModel(AIModel):
    def __init__(self, azure_endpoint, api_key, api_version):
        self.client = AzureOpenAI(azure_endpoint=azure_endpoint, api_key=api_key, api_version=api_version)

    def chat(self, messages, model, temperature, max_tokens):

        resp = self.client.chat.completions.create(model=model, 
                        messages=messages, 
                        temperature=temperature, 
                        max_tokens=max_tokens)
        
        return resp.choices[0].message.content
    
    def moderate(self, message):
        return self.client.moderations.create(input=message)

class AnthropicModel(AIModel):
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)

    def chat(self, messages, model, temperature, max_tokens):
        ## Anthropic requires the system prompt to be passed separately
        ## Hence extracting system prompt role from the messages
        ## and then passing the messages without the system role 
        ## messages is not subscriptable, so we need to convert it to a list
        system_prompt = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")

        # Remove system messages from the list
        user_messages = [m for m in messages if m.get("role") != "system"]
        resp = self.client.messages.create(model=model, 
                                    system=system_prompt,
                                    messages=user_messages,
                                    temperature=temperature, 
                                    max_tokens=max_tokens)
        
        return resp.content[0].text
    
    def moderate(self, message):
        pass

class BedrockModel(AIModel):
    def __init__(self, aws_access_key, aws_secret_key, region, profile_name):
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region,
            profile_name=profile_name if not (aws_access_key and aws_secret_key) else None
        )
        self.client = session.client('bedrock-runtime')
    
    def chat(self, messages, model, temperature, max_tokens):
        if model.startswith("anthropic."):
            return self._anthropic_chat(messages, model, temperature, max_tokens)
        elif model.startswith("amazon."):
            return self._amazon_chat(messages, model, temperature, max_tokens)
        elif model.startswith("meta."):
            return self._meta_chat(messages, model, temperature, max_tokens)
        else:
            return self._anthropic_chat(messages, model, temperature, max_tokens)
    
    def _anthropic_chat(self, messages, model, temperature, max_tokens):
        system_prompt = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        
        formatted_messages = []
        for m in messages:
            if m.get("role") != "system":  # Skip system messages as they're handled separately
                formatted_messages.append({
                    "role": "user" if m.get("role") == "user" else "assistant",
                    "content": m.get("content", "")
                })
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": formatted_messages
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
            
        response = self.client.invoke_model(
            modelId=model,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('content')[0].get('text')
    
    def _amazon_chat(self, messages, model, temperature, max_tokens):
        prompt = ""
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                prompt += f"<system>{content}</system>\n"
            elif role == "user":
                prompt += f"<user>{content}</user>\n"
            elif role == "assistant":
                prompt += f"<assistant>{content}</assistant>\n"
        
        prompt += "<assistant>"
        
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
        }
        
        response = self.client.invoke_model(
            modelId=model,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('results')[0].get('outputText')
    
    def _meta_chat(self, messages, model, temperature, max_tokens):
        prompt = ""
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                prompt += f"<system>\n{content}\n</system>\n"
            elif role == "user":
                prompt += f"<human>\n{content}\n</human>\n"
            elif role == "assistant":
                prompt += f"<assistant>\n{content}\n</assistant>\n"
        
        prompt += "<assistant>\n"
        
        request_body = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }
        
        response = self.client.invoke_model(
            modelId=model,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('generation')
    
    def moderate(self, message):
        pass
