import a2a
from uuid import uuid4
from repositories.game import Game, GameRepository
from game.utils import generate_board_image
from repositories.redis import r as redis_client

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

def handle_final_response(task_id:str, aimove, filename:str, image_url: str):
    response = a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.input_required,
                message=a2a.Message(
                    role="agent",
                    messageId=uuid4().hex,
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