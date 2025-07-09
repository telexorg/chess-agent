import a2a
from uuid import uuid4
from repositories.game import Game, GameRepository
from game.utils import generate_board_image
from repositories.redis import r as redis_client
from repositories.env import CHESS_ENGINE_PATH

game_repo = GameRepository(redis_client)


def handle_user_move_as_board(game: Game):
    image_url, filename = generate_board_image(game.board)
    board_state_response = a2a.SendMessageResponse(
        result=a2a.Message(
            messageId=uuid4().hex,
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
                    messageId=uuid4().hex,
                    role="agent",
                    parts=[
                        a2a.TextPart(text="Game ended by resignation.\n"),
                        a2a.TextPart(text="Start a new game by entering a valid move."),
                    ],
                ),
            ),
        ),
    )


def handle_game_over(task_id: str, aimove, filename: str, image_url: str):
    game_repo.game_over(task_id)

    return a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.completed,
                message=a2a.Message(
                    role="agent",
                    messageId=uuid4().hex,
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


def handle_final_response(task_id: str, aimove, filename: str, image_url: str):
    response = a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            contextId=str(uuid4()),
            status=a2a.TaskStatus(
                state=a2a.TaskState.input_required,
            ),
            artifacts=[
                a2a.Artifact(
                    name="move", parts=[a2a.TextPart(text=f"AI moved {aimove.uci()}")]
                ),
                a2a.Artifact(
                    name="board",
                    parts=[
                        a2a.FilePart(
                            file=a2a.FileContent(
                                name=filename,
                                mimeType="image/svg+xml",
                                uri=image_url,
                            )
                        )
                    ],
                ),
            ],
        )
    )

    return response


def load_or_start_game(task_id: str):
    game = game_repo.load(task_id)
    if not game:
        game = game_repo.start_game(engine_path=CHESS_ENGINE_PATH)
    return game


def build_error_response(message: str, data: str | None = None):
    return a2a.JSONRPCResponse(
        messageId=uuid4().hex,
        error=a2a.InvalidParamsError(message=message, data=data),
    )


def process_user_move(game: Game, user_move: str, task_id: str):
    if user_move == "board":
        return handle_user_move_as_board(game)
    if user_move == "resign":
        return handle_resignation(task_id)

    try:
        game.usermove(user_move)
    except ValueError:
        return build_error_response(
            f"Invalid move: '{user_move}'",
            f"You sent '{user_move}' which is not a valid chess move",
        )
    except:
        return build_error_response("An error occurred")

    return None


async def process_message(task_id: str, user_input: str):
    game = load_or_start_game(task_id)
    user_move = game_repo.parse_command(user_input)

    error_response = process_user_move(game, user_move, task_id)
    if error_response:
        return error_response

    aimove, board = game.aimove()
    game_repo.save(task_id, game)
    image_url, filename = generate_board_image(board)

    if board.is_game_over():
        return handle_game_over(task_id, aimove, filename, image_url)

    return handle_final_response(task_id, aimove, filename, image_url)
