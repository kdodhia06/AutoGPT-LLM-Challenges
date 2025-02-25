from openai import OpenAI

class llm:
    def __init__(self):
        # The full_message_history will store the entire conversation history as is
        # The summarized_message_history  will store a summarized version of the conversation history
        self.full_message_history = []
        self.summarized_message_history = []
        self.client = OpenAI(api_key='')  # OpenAI client with API key
        self.DEBUG = False  # Debug flag
        if self.client.api_key == '':
            raise ValueError("\033[91m Please enter the OpenAI API key which was provided in the challenge email into llm.py.\033[0m")
        
        self.token_threshold_to_trigger_summarization = 1024  # Token threshold to trigger summarization
    
    def add_message_to_history(self, message):
        """
        Adds a message to both the full message history and the summarized message history.

        Args:
            message (dict): A dictionary with 'role' and 'content' keys.
        """
        self.full_message_history.append(message)
        self.summarized_message_history.append(message)

    def calculate_total_tokens(self, messages):
        """
        Calculates the total number of tokens in the message history.

        Args:
            messages (list): A list of messages. Each message is a dictionary with 'role' and 'content' keys.

        Returns:
            int: The total number of tokens in the message history.
        """
        return sum(len(message['content'].split()) for message in messages)

    def summarize_chat_history(self):
        """
        Summarizes the chat history to avoid token limits.

        Returns:
            list: A list of dictionaries. Each dictionary represents a summarized conversation with 'role' and 'content' keys.
        """
        system_prompt = "Summarize this conversation, preserving the most crucial information for maintaining dialogue context:"
        user_prompt = ' '.join([f"{message['role']}: {message['content']}" for message in self.summarized_message_history[:-1]])

        if self.DEBUG:
            print(f"\033[91m  Summarizing chat history... \033[0m")
            print(f"\033[91m  System prompt: {system_prompt} \033[0m")
            print(f"\033[91m  User prompt: {user_prompt} \033[0m")

        response = self.gpt4_one_shot(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        return [{'role': 'system', 'content': response}]

    def manage_context_window(self):
        """
        This function creates the context window to be sent to the LLM. The context window is managed list of messages, and constitutes all the information the LLM knows about the conversation.

        Returns:
            list: The context window to be sent to the LLM.
        """
        # The chat history is summarized only when the token threshold is exceeded.
        # This approach helps to avoid unnecessary computation for summarization and
        # ensures that the most recent messages remain fully intact in the context window.
        # The threshold can be adjusted as required.
        if self.calculate_total_tokens(self.summarized_message_history) >= self.token_threshold_to_trigger_summarization:
            if self.DEBUG:
                print(f"\033[91m  Token threshold exceeded, triggering summarization \033[0m")
            summarized_history = self.summarize_chat_history()
            # Ensure the latest user message is always included
            summarized_history.append(self.summarized_message_history[-1])
            self.summarized_message_history = summarized_history
            if self.DEBUG:
                print(f"\033[91m  Summarized message history: {self.summarized_message_history} \033[0m")

        return self.summarized_message_history

    def send_message(self, prompt: str, role: str = 'user', json_response: bool = False):
        """
        This function adds the provided prompt to the existing message history, creating a context window for the LLM. 
        This context window is forwarded to the LLM. The received response from the LLM is then appended to the message history and returned.

        Args:
            prompt (str): The message content to be sent to the LLM.
            role (str, optional): The role of the speaker. Defaults to 'user'.
                - 'user': Represents the user speaking.
                - 'assistant': Represents the AI assistant speaking.
                - 'system': Represents instructions or context for the AI.
            json_response (bool, optional): Specifies whether the response should be returned as JSON. Defaults to False. If True, schema must be specified.

        Returns:
            str: The AI's response to the message.

        Raises:
            ValueError: If an invalid role is provided.

        Note:
            - The `context_window` is currently using a primitive way of managing conversation history, simply keeping only the last 4 messages.

        Example:
            >>> helper = OpenAIHelper()
            >>> response = helper.send_message("Hello, how can I assist you?")
            >>> print(response)
            "Sure, I can help you with that!"
        """
        if role == 'user':
            self.add_message_to_history({'role': 'user', 'content': prompt})
        elif role == 'assistant':
            self.add_message_to_history({'role': 'assistant', 'content': prompt})
        elif role == 'system':
            self.add_message_to_history({'role': 'system', 'content': prompt})
        else:
            raise ValueError("Invalid role provided. Valid roles are 'user', 'assistant', or 'system'.")

        context_window = self.manage_context_window()

        if self.DEBUG:
            print(f"\033[91m  Context sent to LLM:\n  {context_window} \033[0m")

        # Send the message to the LLM and get the response.
        response = self.gpt4_conversation(context_window)

        ai_message = response.choices[0].message.content

        self.add_message_to_history({'role': 'assistant', 'content': ai_message})
        return ai_message

    #~#~#~# Methods for interacting with OpenAI's Chat Completions EndPoint - You probably won't need to edit anything below this line. #~#~#~#
    def gpt4_conversation(self, messages: list, json_response: bool = False, model: str = "gpt-4-1106-preview"):
        """
        Initiates a conversation with the GPT-4 language model using the specified parameters.

        This method sends a list of messages to the GPT-4 model and retrieves the model's response. It allows configuration 
        of the model and response format.

        Args:
            messages (list): A list of message objects (dicts) that form the conversation history (context window).
            json_response (bool, optional): If True, forces the response to be in JSON format. Requires a defined response schema somewhere in the messages.
                                            Defaults to False.
            model (str, optional): The specific GPT-4 model version to be used for the conversation. Defaults to "gpt-4-1106-preview".

        Returns:
            response: The response from the GPT-4 model. Format: https://platform.openai.com/docs/api-reference/chat/object

        Raises:
            ValueError: If the combined token count of the response and context exceeds the 4096 token limit.

        Note:
            - The 'temperature' parameter controls the randomness of the model's responses. A higher value increases randomness.
            - The 'max_tokens' parameter sets the limit for the response token count. Exceeding this limit triggers a ValueError.
            - The method currently imposes a shorter context window limit for this specific implementation.
        
        Example:
            >>> response = gpt4_conversation([{'role': 'user', 'content': 'Hello, AI!'}])
            >>> print(response)
        """
        # Initialize the conversation with the GPT-4 model
        response = self.client.chat.completions.create(
            model=model,  # Specifies the GPT-4 model version
            temperature=0.79,  # Sets the AI's creativity level. Higher values increase randomness.
            max_tokens=4096,  # Sets the maximum number of tokens in the AI's response.
            response_format={"type": "json_object"} if json_response else None,  # Optional JSON response format
            messages=messages  # The conversation history to be sent to the model
        )

        # Check if the total token usage exceeds the limit
        # DO NOT CHANGE THIS - This is a requirement for the challenge.
        if response.usage.total_tokens > 4096:
            raise ValueError("CHALLENGE CONTEXT WINDOW EXCEEDED: The context window now exceeds the 4096 token limit. Please try again with a shorter prompt.")

        return response

    
    def gpt4_one_shot(self, system_prompt: str, user_prompt: str, json_response: bool = False, model: str = "gpt-4-1106-preview"):
        """
        Executes a one-shot completion with the GPT-4 language model, using both a system and a user prompt.

        This method is designed for scenarios where a single interaction with the GPT-4 model is required, rather than a 
        continuous conversation. It allows specifying both a system-level and a user-level prompt to guide the model's response.

        Args:
            system_prompt (str): The system-level prompt that sets the context or instructions for the model.
            user_prompt (str): The user's input or question to the model.
            json_response (bool, optional): If True, forces the response to be in JSON format. Requires a defined response schema.
                                            Defaults to False.
            model (str, optional): The specific GPT-4 model version to be used for the completion. Defaults to "gpt-4-1106-preview".

        Returns:
            str: The content of the model's response message as a string.

        Raises:
            ValueError: If the combined token count of the response and prompts exceeds the 4096 token limit.

        Note:
            - The 'temperature' parameter influences the model's creativity and unpredictability.
            - The 'max_tokens' parameter sets a limit on the response size.
            - This method is suitable for tasks like generating content, answering questions, or other one-off tasks.
        
        Example:
            >>> response = gpt4_one_shot("Always respond in French.", "Tell a one scentence poem about a robot's adventure.")
            >>> print(response)
            "Un robot solitaire, vers les étoiles il vole, son aventure commence, un rêve qui se dévoile."
        """
        # Initialize a one-shot completion with the GPT-4 model
        response = self.client.chat.completions.create(
            model=model,  # Specifies the GPT-4 model version
            temperature=0.79,  # Sets the AI's creativity level
            max_tokens=4096,  # Limits the response token count
            response_format={"type": "json_object"} if json_response else None,  # Optional JSON response format
            messages=[
                {"role": "system", "content": system_prompt},  # System-level context or instruction
                {"role": "user", "content": user_prompt}  # User input or question
            ]
        )

        # Check if the total token usage exceeds the limit
        # DO NOT CHANGE THIS - This is a requirement for the challenge.
        if response.usage.total_tokens > 4096:
            raise ValueError("CHALLENGE CONTEXT WINDOW EXCEEDED: The context window now exceeds the 4096 token limit. Please try again with a shorter prompt.")

        return response.choices[0].message.content