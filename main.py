import os
import json
import base64
import random
import datetime
import httpx
from typing import Tuple, Optional, Any
from dataclasses import dataclass
from fastapi import FastAPI, BackgroundTasks, Request, Body, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from uuid import uuid4 as uuid
import a2a
import redis
import chess
import chess.engine
from minio import Minio
from minio.error import S3Error

load_dotenv()
app = FastAPI()

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
CHESS_ENGINE_PATH = os.getenv("CHESS_ENGINE_PATH")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")
MINIO_BUCKET_ACCESS_KEY = os.getenv("MINIO_BUCKET_ACCESS_KEY")
MINIO_BUKCET_SECRET_KEY = os.getenv("MINIO_BUKCET_SECRET_KEY")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_BUCKET_ACCESS_KEY,
    secret_key=MINIO_BUKCET_SECRET_KEY,
)


@dataclass
class RedisKeys:
    games = "games"


class RandomNameRepository:
    WORDS = [
        "sun", "moon", "tree", "cloud", "river", "stone", "eagle", "wolf", "fire",
        "wind", "storm", "leaf", "sky", "night", "light", "shadow", "mountain",
        "ocean", "echo", "whisper", "flame", "dust", "branch",
    ]

    @classmethod
    def generate_filename(cls, extension: str = "svg", word_count: int = 3) -> str:
        words = random.sample(cls.WORDS, word_count)
        return "_".join(words) + f".{extension}"

    @classmethod
    def generate_suffix(cls, word_count: int = 2) -> str:
        return "_".join(random.sample(cls.WORDS, word_count))

class Game:
    def __init__(self, board, engine, engine_time_limit=0.5, state=a2a.TaskState.unknown):
        self.board = board
        self.engine = engine
        self.engine_time_limit = engine_time_limit
        self.state = state

    def aimove(self):
        ai = self.engine.play(
            self.board, chess.engine.Limit(time=self.engine_time_limit)
        )
        self.board.push(ai.move)
        self.state = a2a.TaskState.input_required
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
            state = a2a.TaskState(state_str)
        except ValueError:
            state = a2a.TaskState.unknown

        return cls(board, engine, engine_time_limit, state)


class GameRepository:
    def __init__(self, redis_client, redis_key_prefix=RedisKeys.games):
        self.r = redis_client
        self.prefix = redis_key_prefix

    def _game_key(self, task_id: str) -> str:
        return f"{self.prefix}:{task_id}"

    def task_state(self, task_id: str) -> a2a.TaskState:
        key = self._game_key(task_id)
        data = self.r.get(key)
        if data:
            data_json = json.loads(data)
            state_str = data_json.get("state", "unknown")
            try:
                return a2a.TaskState(state_str)
            except ValueError:
                return a2a.TaskState.unknown

        return a2a.TaskState.unknown

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
            game.state = a2a.TaskState.completed
            self.save(task_id, game)

    def delete(self, task_id: str):
        key = self._game_key(task_id)
        self.r.delete(key)

    def start_game(self, engine_path: str) -> Game:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        board = chess.Board()

        return Game(board, engine)

    def parse_command(self, message: str) -> str:
        message = message.strip()
        message_lowercase = message.lower()

        if "resign" in message_lowercase:
            return "resign"
        if "board" in message_lowercase:
            return "board"

        return message


@app.get("/", response_class=HTMLResponse)
def read_root():
    return '<p style="font-size:40px">Chess bot A2A</p>'


def generate_board_image(board):
    filename = RandomNameRepository.generate_filename()
    destination_file = f"public/chessagent/{filename}"
    source_file = f"/tmp/{filename}"

    svg = board._repr_svg_()

    with open(source_file, "w") as f:
        f.write(svg)
        new_source_file = source_file.split(".svg")[0] + ".png"

        import cairosvg

        cairosvg.svg2png(url=source_file, write_to=new_source_file)

        source_file = new_source_file
        destination_file = destination_file.split(".svg")[0] + ".png"

    minio_client.fput_object(
        MINIO_BUCKET_NAME,
        destination_file,
        source_file,
    )

    image_url = f"https://media.tifi.tv/{MINIO_BUCKET_NAME}/{destination_file}"

    return image_url, filename


game_repo = GameRepository(r)

def handle_user_move_as_board(game: Game):
    image_url, filename = generate_board_image(game.board)
    board_state_response = a2a.SendMessageResponse(
        result=a2a.Message(
            messageId=uuid().hex,
            role="agent",
            parts=[
                a2a.TextPart(text="Board state is:"),
                a2a.FilePart(
                    file=a2a.FileContent(
                        name=filename,
                        mimeType="image/svg+xml",
                        uri=image_url,
                    )
                ),
            ],
        ),
    )
    return board_state_response

def handle_resignation(task_id: str):
    game_repo.game_over(task_id)
    return a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.completed,
                message=a2a.Message(
                    messageId=uuid().hex,
                    role="agent",
                    parts=[
                        a2a.TextPart(text="Game ended by resignation.\n"),
                        a2a.TextPart(
                            text="Start a new game by entering a valid move."
                        ),
                    ],
                ),
            ),
        ),
    )

def handle_game_over(task_id:str, aimove, filename:str, image_url:str):
    game_repo.game_over(task_id)

    return a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.completed,
                message=a2a.Message(
                    role="agent",
                    messageId=uuid().hex,
                    parts=[
                        a2a.TextPart(text=f"Game over. AI moved {aimove.uci()}"),
                        a2a.FilePart(
                            file=a2a.FileContent(
                                name=filename,
                                mimeType="image/svg+xml",
                                uri=image_url,
                            )
                        ),
                        a2a.TextPart(text="Start a new game by entering a valid move"),
                    ],
                ),
            ),
        ),
    )

def handle_final_response(task_id:str, aimove, filename:str, image_url: str):
    response = a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.input_required,
                message=a2a.Message(
                    role="agent",
                    messageId=uuid().hex,
                    parts=[
                        a2a.TextPart(text=f"AI moved {aimove.uci()}"),
                        # a2a.TextPart(text=str(board)),
                        a2a.FilePart(
                            file=a2a.FileContent(
                                name=filename,
                                mimeType="image/svg+xml",
                                uri=image_url,
                            )
                        ),
                    ],
                ),
            ),
        ),
    )

    return response


async def handle_message_send(params: a2a.MessageSendParams):
    task_id = uuid().hex if not params.message.taskId else params.message.taskId
    game = game_repo.load(task_id)

    if not game:
        game = game_repo.start_game(engine_path=CHESS_ENGINE_PATH)

    user_input = params.message.parts[0].text.strip()
    user_move = game_repo.parse_command(user_input)

    if user_move == "board":
        return handle_user_move_as_board(game)

    if user_move == "resign":
        return handle_resignation(task_id)

    try:
        game.usermove(user_move)
    except ValueError:
        response = a2a.JSONRPCResponse(
            messageId=uuid().hex,
            error=a2a.InvalidParamsError(
                message=f"Invalid move: '{user_move}'",
                data=f"You sent '{user_move}' which is not a valid chess move",
            ),
        )
        return response
    except:
        response = a2a.JSONRPCResponse(
            messageId=uuid().hex,
            error=a2a.InvalidParamsError(
                message="An error occured",
            ),
        )
        return response

    aimove, board = game.aimove()
    game_repo.save(task_id, game)
    image_url, filename = generate_board_image(board)

    if board.is_game_over():
        return handle_game_over(task_id, aimove, filename, image_url)

    return handle_final_response(task_id, aimove, filename, image_url)



async def handle_get_task(params: a2a.TaskQueryParams):
    task_state = game_repo.task_state(params.id)

    response = a2a.GetTaskResponse(
        result=a2a.Task(
            id=params.id,
            status=a2a.TaskStatus(
                state=task_state,
                message=a2a.Message(
                    messageId=uuid().hex,
                    role="agent",
                    parts=[
                        a2a.TextPart(text=f"The current task state is {task_state}"),
                    ],
                ),
            ),
        ),
    )

    return response

def safe_get(obj, *attrs):
    for attr in attrs:
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return obj


async def actual_messaging(params: a2a.MessageSendParams, task_id:str, webhook_url: str, auth_headers: dict[str, Any]):
    game = game_repo.load(task_id)

    if not game:
        game = game_repo.start_game(engine_path=CHESS_ENGINE_PATH)

    user_input = params.message.parts[0].text.strip()
    user_move = game_repo.parse_command(user_input)

    error_response = None

    try:
        game.usermove(user_move)
    except ValueError:
        error_response = a2a.JSONRPCResponse(
            messageId=uuid().hex,
            error=a2a.InvalidParamsError(
                message=f"Invalid move: '{user_move}'",
                data=f"You sent '{user_move}' which is not a valid chess move",
            ),
        )
        
    except:
        error_response = a2a.JSONRPCResponse(
            messageId=uuid().hex,
            error=a2a.InvalidParamsError(
                message="An error occured",
            ),
        )

    if error_response:
        res = httpx.post(webhook_url, json=error_response.model_dump())
        print(res)

    aimove, board = game.aimove()
    game_repo.save(task_id, game)
    image_url, filename = generate_board_image(board)

    final_response = handle_final_response(task_id, aimove, filename, image_url)

    print(webhook_url, final_response.model_dump_json())
    res = httpx.post(webhook_url, headers=auth_headers, json=final_response.model_dump())
    print(res)

async def handle_message_send_with_webhook(params: a2a.MessageSendParams, background_tasks: BackgroundTasks):
    webhook_url = safe_get(params, "configuration", "pushNotificationConfig", "url")
    scheme = safe_get(params, "configuration", "pushNotificationConfig", "authentication", "schemes")
    credential = safe_get(params, "configuration", "pushNotificationConfig", "authentication", "credentials")

    auth_headers = {}

    if "TelexApiKey" in scheme:
        auth_headers["X-TELEX-API-KEY"] = credential

    if not webhook_url:
        return a2a.JSONRPCResponse(
            messageId=uuid().hex,
            error=a2a.InvalidParamsError(
                message="No webhook URL provided, but is necessary",
            ),
        )
    
    existing_task_id = params.message.taskId
    task_id = existing_task_id if existing_task_id else uuid().hex

    background_tasks.add_task(actual_messaging, params, task_id, webhook_url, auth_headers)


    return a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.working
            )
        ),
    )


@app.post("/")
async def handle_rpc(request_data: dict, background_tasks: BackgroundTasks):
    try:
        # Parse the request using the TypeAdapter
        rpc_request = a2a.A2ARequest.validate_python(request_data)

        if isinstance(rpc_request, a2a.SendMessageRequest):
            print("Recieved message/send")
            return await handle_message_send(params=rpc_request.params)
            # return await handle_message_send_with_webhook(params=rpc_request.params, background_tasks=background_tasks)
        elif isinstance(rpc_request, a2a.GetTaskRequest):
            print("tasks/get")
            return await handle_get_task(params=rpc_request.params)
        else:
            raise HTTPException(status_code=400, detail="Method not supported")
            
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=400, detail="Could not handle task")

agent_name_suffix = (
    "-" + os.getenv("APP_ENV") + "_" + RandomNameRepository.generate_suffix()
    if os.getenv("APP_ENV") == "local"
    else ""
)

@app.get("/.well-known/agent.json")
def agent_card(request: Request):
    external_base = request.headers.get("x-external-base-url", "")
    base_url = str(request.base_url).rstrip("/") + external_base
    card = a2a.AgentCard(
        name=f"Chess Agent {agent_name_suffix}",
        description="An agent that plays chess. Accepts moves in standard notation and returns updated board state as FEN and an image.",
        url=f"{base_url}",
        provider=a2a.AgentProvider(
            organization="CoolVicradon",
            url=f"{base_url}/provider",
        ),
        version="1.0.0",
        documentationUrl=f"{base_url}/docs",
        capabilities=a2a.AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=True,
        ),
        authentication=a2a.AgentAuthentication(schemes=["Bearer"]),
        defaultInputModes=["text/plain"],
        defaultOutputModes=["application/x-fen", "image/png"],
        skills=[
            a2a.AgentSkill(
                id="play_move",
                name="Play Move",
                description="Plays a move and returns the updated board in FEN format and as an image.",
                tags=["chess", "gameplay", "board"],
                examples=["e4", "Nf3", "d5"],
                inputModes=["text/plain"],
                outputModes=["application/x-fen", "image/png"],
            )
        ],
    )

    return card


if __name__ == "__main__":
    import uvicorn

    PORT = int(os.getenv("PORT", 7000))

    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
