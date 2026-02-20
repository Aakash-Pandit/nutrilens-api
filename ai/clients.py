import os

import cohere

from ai.prompts import PREAMBLE
from ai.tools import AI_TOOLS, get_ai_function_map
from organizations.constants import get_organization_function_map
from organizations.tools import ORGANIZATION_TOOLS


class CohereClient:
    def __init__(
        self,
        message: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
    ):
        self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
        self.model = model or os.getenv("COHERE_LLM_MODEL")
        self.preamble = PREAMBLE
        self.function_map = {
            **get_organization_function_map(user_id=user_id),
            **get_ai_function_map(user_id=user_id),
        }
        tools = [*ORGANIZATION_TOOLS, *AI_TOOLS]
        if user_id is None:
            tools = [
                t
                for t in tools
                if t.get("name")
                not in (
                    "get_my_organization_details",
                    "search_my_organization_policies",
                    "get_my_pending_leaves",
                )
            ]
        self.tools = tools
        self.message = message or ""

    def chat(
        self,
        message: str,
        tool_results: list | None = None,
        chat_history: list | None = None,
    ) -> str:
        response = self.client.chat(
            message=message,
            tools=self.tools,
            preamble=self.preamble,
            model=self.model,
            tool_results=tool_results,
            chat_history=chat_history,
        )
        return response

    def update_tools_results(self, response: cohere.ChatResponse) -> list:
        tool_results = []
        for tool_call in response.tool_calls or []:
            raw_parameters = tool_call.parameters or {}
            parameters = dict(raw_parameters)
            try:
                output = self.function_map[tool_call.name](**parameters)
            except Exception as exc:
                output = {
                    "error": str(exc),
                    "tool": tool_call.name,
                    "parameters": parameters,
                }
            tool_results.append(
                {
                    "call": tool_call,
                    "outputs": [output],
                }
            )

        return tool_results

    def ask_llm(
        self,
        message: str | None = None,
        chat_history: list | None = None,
        max_steps: int = 8,
    ) -> tuple[str, list]:
        try:
            history = list(chat_history or [])
            prompt = self.message if message is None else message
            response = None
            tool_results = None
            steps = 0
            while steps < max_steps:
                history_for_chat = history
                if tool_results and history and history[-1]["role"] == "USER":
                    history_for_chat = history[:-1]
                response = self.chat(
                    message=prompt if steps == 0 else "",
                    tool_results=tool_results,
                    chat_history=history_for_chat,
                )
                if steps == 0 and prompt:
                    history.append({"role": "USER", "message": prompt})
                if response.text:
                    history.append({"role": "CHATBOT", "message": response.text})
                elif response.tool_calls:
                    history.append({"role": "CHATBOT", "message": "Tool call issued."})
                if not response.tool_calls:
                    break
                tool_results = self.update_tools_results(response)
                steps += 1
            if response and response.tool_calls and steps >= max_steps:
                return (
                    "I couldn't complete that within the allowed steps. Please "
                    "confirm details or try a specific date/time.",
                    history,
                )
        except Exception as e:
            return str(e), chat_history or []

        return (response.text if response else ""), history

    def embed_texts(self, texts: list[str], input_type: str) -> list[list[float]]:
        response = self.client.embed(
            texts=texts,
            model=self.model,
            input_type=input_type,
        )
        return response.embeddings or []
