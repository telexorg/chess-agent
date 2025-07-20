import os
from typing import Optional, Literal
from pydantic import ConfigDict, BaseModel, Field
from pydantic_ai import Agent, RunContext
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
    fen: str


class ChessCommandResponse(BaseModel):
    """Response from the chess agent parsing user input."""

    command_type: Literal["resign", "board", "move", "chat", "unknown"] = Field(
        description="Type of command parsed from user input"
    )

    move: Optional[str] = Field(
        default=None,
        description="Chess move in algebraic notation (only present when command_type is 'move')",
    )

    chat_query_response: Optional[str] = Field(
        default=None,
        description="A string response containing an answer to a user's query (only present when command_type is 'chat')",
    )

    message: Optional[str] = Field(
        default=None, 
        description="Simple message for unknown commands"
    )


chess_agent = Agent(
    model,
    deps_type=AgentDependencies,
    retries=2,
    output_type=ChessCommandResponse
)


def game_context(moves: list[str]):
    game_phase = ""
    context_hint = ""

    move_count = len(moves)
    if move_count == 0:
        game_phase = "opening"
        context_hint = "The game is just starting."
    elif move_count < 20:
        game_phase = "early game"
        context_hint = f"We're in the early game with {move_count} moves played."
    elif move_count < 40:
        game_phase = "middle game"
        context_hint = f"We're in the middle game with {move_count} moves played."
    else:
        game_phase = "endgame"
        context_hint = f"We're in the endgame with {move_count} moves played."

    return (game_phase, context_hint)
    

def get_move_history_text(moves: list[str]):
    if moves:
        recent_moves = moves[-6:]  # Show last 6 moves for context
        move_history_text = f"Recent moves: {', '.join(recent_moves)}"
        if len(moves) > 6:
            move_history_text = f"Last moves: {', '.join(recent_moves)} (showing last 6 of {len(moves)} total)"
    else:
        move_history_text = "No moves have been made yet."

    return move_history_text

@chess_agent.system_prompt
def get_system_prompt(ctx: RunContext[AgentDependencies]) -> str:
    """Generate a context-aware system prompt based on current game state."""
    
    current_fen = ctx.deps.fen
    moves = ctx.deps.move_history


    return f"""
    You are a Chess Agent that interprets user input for a chess game.
    The move history is :{moves} and the fen is :{current_fen}.

    Respond with one of these command types:
    1. 'resign' — user wants to quit
    2. 'board' — user wants to see current position
    3. 'move' — convert input to valid chess move in algebraic notation
    4. 'chat' — answer chess questions or discuss the game
    5. 'unknown' — input doesn't fit any category

    For natural language moves like 'castle kingside', 'take the pawn', or 'develop knight', 
    convert to proper algebraic notation (O-O, Nxe5, Nf3, etc.).

    For strategic requests like 'play aggressively' or 'something safe', suggest an appropriate move as a chat.

    For chess questions, provide helpful answers. If unsure, say so.

    For unclear input, use 'unknown' with a brief message asking what they meant.
    """
