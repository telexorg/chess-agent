import os
import json
import chess
import chess.engine
import schemas
from typing import Optional, Literal
from repositories.redis import RedisKeys
from repositories.env import CHESS_ENGINE_PATH
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

class ChessCommandResponse(BaseModel):
    """Response from the chess agent parsing user input."""
    
    command_type: Literal["resign", "board", "move", "invalid"] = Field(
        description="Type of command parsed from user input"
    )
    
    move: Optional[str] = Field(
        default=None,
        description="Chess move in algebraic notation (only present when command_type is 'move')"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message for invalid commands"
    )


chess_agent = Agent(
    model,
    deps_type=AgentDependencies,
    retries=2,
    output_type=ChessCommandResponse,
    system_prompt=(
        "You are a Chess Agent."
        "Your job is to interpret a user's input and respond with one of the following:"
        "1. 'resign' — if the user wants to quit or give up."
        "2. 'board' — if the user wants to see the current board state."
        "3. A valid chess move in standard algebraic notation (e.g., 'e4', 'Nf3')."
        "For natural language requests such as 'make the most popular first move' or 'play something aggressive', infer the most appropriate move and return it in algebraic notation."
        "Use known chess opening theory and standard practices to interpret such requests when possible."
        "If the input does not match any of the above categories or cannot be interpreted into a valid action, respond with 'invalid command' and include a brief error explanation if helpful."
    )
)

class Game:
    def __init__(self, board: chess.Board, engine: chess.engine.SimpleEngine, engine_time_limit=0.5, state=schemas.TaskState.unknown):
        self.board = board
        self.engine = engine
        self.engine_time_limit = engine_time_limit
        self.state = state

    def aimove(self):
        ai = self.engine.play(
            self.board, chess.engine.Limit(time=self.engine_time_limit)
        )
        self.board.push(ai.move)
        self.state = schemas.TaskState.input_required
        return ai.move, self.board

    def usermove(self, move):
        try:
            self.board.push_san(move)
        except ValueError:
            raise ValueError(f"Invalid move: {move}")
        return self.board

    def to_dict(self):
        return {"fen": self.board.fen(), "engine_time_limit": self.engine_time_limit, "state": self.state.value}

    @classmethod
    def from_dict(cls, data):
        board = chess.Board(data["fen"])
        engine_time_limit = data.get("engine_time_limit", 0.5)
        engine = chess.engine.SimpleEngine.popen_uci(CHESS_ENGINE_PATH)
        state_str = data.get("state", "unknown")

        try:
            state = schemas.TaskState(state_str)
        except ValueError:
            state = schemas.TaskState.unknown

        return cls(board, engine, engine_time_limit, state)


class GameRepository:
    def __init__(self, redis_client, redis_key_prefix=RedisKeys.games):
        self.r = redis_client
        self.prefix = redis_key_prefix

    def _game_key(self, task_id: str) -> str:
        return f"{self.prefix}:{task_id}"

    def task_state(self, task_id: str) -> schemas.TaskState:
        key = self._game_key(task_id)
        data = self.r.get(key)
        if data:
            data_json = json.loads(data)
            state_str = data_json.get("state", "unknown")
            try:
                return schemas.TaskState(state_str)
            except ValueError:
                return schemas.TaskState.unknown

        return schemas.TaskState.unknown

    def save(self, task_id: str, game: Game):
        key = self._game_key(task_id)
        self.r.set(key, json.dumps(game.to_dict()))

    def load(self, task_id: str) -> Optional[Game]:
        key = self._game_key(task_id)
        data = self.r.get(key)
        if data:
            return Game.from_dict(json.loads(data))
        return None

    def game_over(self, task_id: str):
        game = self.load(task_id)
        if game:
            game.state = schemas.TaskState.completed
            self.save(task_id, game)

    def delete(self, task_id: str):
        key = self._game_key(task_id)
        self.r.delete(key)

    def start_game(self, engine_path: str) -> Game:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        board = chess.Board()

        return Game(board, engine)


    async def parse_command(self, message: str) -> ChessCommandResponse:
        result = await chess_agent.run(message.strip(), deps=AgentDependencies())
        return result.output
