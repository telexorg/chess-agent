import schemas
from uuid import uuid4
from repositories.game import Game, GameRepository
from game.utils import generate_board_image
from repositories.redis import r as redis_client
from repositories.env import CHESS_ENGINE_PATH
from repositories.game import ChessCommandResponse

game_repo = GameRepository(redis_client)


def get_board_state(game: Game):
    image_url, filename = generate_board_image(game.board)
    board_state_response = schemas.SendMessageResponse(
        result=schemas.Message(
            messageId=uuid4().hex,
            role="agent",
            parts=[
                schemas.TextPart(text="Board state is:"),
                schemas.FilePart(
                    file=schemas.FileContent(
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
    return schemas.SendMessageResponse(
        result=schemas.Task(
            id=task_id,
            status=schemas.TaskStatus(
                state=schemas.TaskState.completed,
            ),
            artifacts=[
                schemas.Artifact(
                    parts=[
                        schemas.TextPart(text="Game ended by resignation.\n"),
                        schemas.TextPart(
                            text="Start a new game by entering a valid move."
                        ),
                    ],
                )
            ],
        ),
    )


def handle_game_over(task_id: str, aimove, filename: str, image_url: str):
    game_repo.game_over(task_id)

    return schemas.SendMessageResponse(
        result=schemas.Task(
            id=task_id,
            status=schemas.TaskStatus(state=schemas.TaskState.completed),
            artifacts=[
                schemas.Artifact(
                    parts=[
                        schemas.TextPart(text=f"Game over. AI moved {aimove.uci()}"),
                        schemas.FilePart(
                            file=schemas.FileContent(
                                name=filename,
                                mimeType="image/svg+xml",
                                uri=image_url,
                            )
                        ),
                        schemas.TextPart(
                            text="Start a new game by entering a valid move"
                        ),
                    ],
                )
            ],
        ),
    )


def handle_final_response(task_id: str, aimove, filename: str, image_url: str):
    response = schemas.SendMessageResponse(
        result=schemas.Task(
            id=task_id,
            contextId=str(uuid4()),
            status=schemas.TaskStatus(
                state=schemas.TaskState.input_required,
            ),
            artifacts=[
                schemas.Artifact(
                    name="move",
                    parts=[schemas.TextPart(text=f"AI moved {aimove.uci()}")],
                ),
                schemas.Artifact(
                    name="board",
                    parts=[
                        schemas.FilePart(
                            file=schemas.FileContent(
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
    return schemas.JSONRPCResponse(
        messageId=uuid4().hex,
        error=schemas.InvalidParamsError(message=message, data=data),
    )


def process_user_move(game: Game, command_response: ChessCommandResponse, task_id: str):
    if command_response.command_type == "board":
        return get_board_state(game)

    if command_response.command_type == "resign":
        return handle_resignation(task_id)

    if command_response.command_type == "invalid":
        return build_error_response(
            "Invalid command",
            command_response.error_message or "Command not recognized",
        )

    if command_response.command_type == "move":
        if not command_response.move:
            return build_error_response(
                "No move provided", "Move command requires a chess move"
            )

        try:
            game.usermove(command_response.move)
        except ValueError:
            return build_error_response(
                f"Invalid move: '{command_response.move}'",
                f"'{command_response.move}' is not a valid chess move",
            )
        except Exception:
            return build_error_response("An error occurred")

    return None


async def process_message(task_id: str, user_input: str):
    game = load_or_start_game(task_id)
    command_response = await game_repo.parse_command(user_input, game)

    print(f"Command response is {command_response}")

    error_response = process_user_move(game, command_response, task_id)
    if error_response:
        return error_response

    if command_response.command_type == "move":
        aimove, board = game.aimove()
        game_repo.save(task_id, game)

    image_url, filename = generate_board_image(board)

    if board.is_game_over():
        return handle_game_over(task_id, aimove, filename, image_url)

    return handle_final_response(task_id, aimove, filename, image_url)
