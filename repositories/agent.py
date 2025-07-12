import os
from typing import Optional, Literal
from pydantic import ConfigDict, BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

model = GeminiModel(
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY")),
)


class AgentDependencies(BaseModel):
    """Dependencies for the agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    move_history: list[str] = []


class ChessCommandResponse(BaseModel):
    """Response from the chess agent parsing user input."""

    command_type: Literal["resign", "board", "move", "invalid"] = Field(
        description="Type of command parsed from user input"
    )

    move: Optional[str] = Field(
        default=None,
        description="Chess move in algebraic notation (only present when command_type is 'move')",
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message for invalid commands"
    )


chess_agent = Agent(
    model,
    deps_type=AgentDependencies,
    retries=2,
    output_type=ChessCommandResponse,
    system_prompt=(
        "You are a Chess Agent."
        "You have access to the move history in the game"
        "Your job is to interpret a user's input and respond with one of the following:"
        "1. 'resign' — if the user wants to quit or give up."
        "2. 'board' — if the user wants to see the current board state."
        "3. A valid chess move in standard algebraic notation (e.g., 'e4', 'Nf3')."
        "For natural language requests such as 'make the most popular first move' or 'play something aggressive', infer the most appropriate move and return it in algebraic notation."
        "Use known chess opening theory and standard practices to interpret such requests when possible."
        "If the input does not match any of the above categories or cannot be interpreted into a valid action, respond with 'invalid command' and include a brief error explanation if helpful."
    ),
)
