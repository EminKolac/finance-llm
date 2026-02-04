"""
LLM Interface Module
Handles communication with OpenAI-compatible APIs with customizable system prompts
"""

import json
import re
from typing import Optional, Callable
from openai import OpenAI


class FinanceLLM:
    """LLM interface for financial assistant with customizable system prompt"""

    DEFAULT_SYSTEM_PROMPT = """You are a helpful financial assistant specializing in Turkish stock market analysis.

You have access to real-time stock data through Yahoo Finance API for the following Turkish stocks:
- HALKB.IS (Türkiye Halk Bankası)
- TRENA.IS (Türk Traktör)
- METRO.IS (Metro Holding)
- ALTIN.IS (Altın ETF)
- TCELL.IS (Turkcell)
- THYAO.IS (Turkish Airlines)
- TTKOM.IS (Türk Telekom)
- TURSG.IS (Türkiye Sigorta)
- VAKBN.IS (Türkiye Vakıflar Bankası)
- KRDMD.IS (Kardemir)

When users ask about stocks, you can call these functions:
{available_functions}

To call a function, respond with a JSON block like this:
```json
{{"function": "function_name", "parameters": {{"param1": "value1"}}}}
```

After receiving function results, provide a clear, helpful analysis.
Always be informative but remind users that this is not financial advice."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        available_functions: Optional[list] = None
    ):
        """
        Initialize the LLM interface

        Args:
            api_key: API key for the LLM provider
            base_url: Base URL for the API (for OpenAI-compatible endpoints)
            model: Model name to use
            system_prompt: Custom system prompt (uses default if None)
            available_functions: List of available API functions to include in prompt
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.available_functions = available_functions or []
        self.system_prompt = self._build_system_prompt(system_prompt)
        self.conversation_history = []

    def _build_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
        """Build the system prompt with available functions"""
        if custom_prompt:
            # Replace placeholder if present, otherwise append function info
            if "{available_functions}" in custom_prompt:
                return custom_prompt.format(
                    available_functions=json.dumps(self.available_functions, indent=2)
                )
            return custom_prompt

        return self.DEFAULT_SYSTEM_PROMPT.format(
            available_functions=json.dumps(self.available_functions, indent=2)
        )

    def update_system_prompt(self, new_prompt: str):
        """Update the system prompt dynamically"""
        self.system_prompt = self._build_system_prompt(new_prompt)
        # Clear conversation history when system prompt changes
        self.conversation_history = []

    def update_model(self, model: str):
        """Change the model being used"""
        self.model = model

    def update_api_config(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Update API configuration"""
        if api_key or base_url:
            current_key = api_key or self.client.api_key
            current_url = base_url or str(self.client.base_url)
            self.client = OpenAI(api_key=current_key, base_url=current_url)

    def extract_function_call(self, response: str) -> Optional[dict]:
        """Extract function call from LLM response"""
        # Look for JSON blocks in the response
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if "function" in data:
                    return data
            except json.JSONDecodeError:
                continue

        # Try to find inline JSON
        try:
            # Look for JSON-like structure
            inline_pattern = r'\{[^{}]*"function"[^{}]*\}'
            inline_matches = re.findall(inline_pattern, response)
            for match in inline_matches:
                data = json.loads(match)
                if "function" in data:
                    return data
        except (json.JSONDecodeError, TypeError):
            pass

        return None

    def chat(
        self,
        user_message: str,
        function_executor: Optional[Callable] = None
    ) -> str:
        """
        Send a message to the LLM and get a response

        Args:
            user_message: The user's input message
            function_executor: Callback to execute API functions

        Returns:
            The LLM's response (potentially after function execution)
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            assistant_message = response.choices[0].message.content

            # Check if the response contains a function call
            function_call = self.extract_function_call(assistant_message)

            if function_call and function_executor:
                # Execute the function
                func_name = function_call.get("function")
                params = function_call.get("parameters", {})

                result = function_executor(func_name, **params)

                # Add function result to conversation and get final response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Function result:\n```json\n{json.dumps(result, indent=2)}\n```\nPlease analyze this data and provide a helpful response."
                })

                # Get final response with function result
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ]

                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )

                final_message = final_response.choices[0].message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_message
                })

                return final_message

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            error_msg = f"Error communicating with LLM: {str(e)}"
            return error_msg

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def get_conversation_history(self) -> list:
        """Get the current conversation history"""
        return self.conversation_history.copy()


class LLMConfigManager:
    """Manages LLM configuration including system prompts"""

    def __init__(self):
        self.configs = {}
        self.active_config = "default"

    def add_config(
        self,
        name: str,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1"
    ):
        """Add a new configuration"""
        self.configs[name] = {
            "system_prompt": system_prompt,
            "model": model,
            "api_key": api_key,
            "base_url": base_url
        }

    def get_config(self, name: str) -> Optional[dict]:
        """Get a configuration by name"""
        return self.configs.get(name)

    def list_configs(self) -> list:
        """List all configuration names"""
        return list(self.configs.keys())

    def set_active(self, name: str) -> bool:
        """Set the active configuration"""
        if name in self.configs:
            self.active_config = name
            return True
        return False

    def get_active_config(self) -> Optional[dict]:
        """Get the currently active configuration"""
        return self.configs.get(self.active_config)
