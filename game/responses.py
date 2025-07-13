import uuid
from game.utils import generate_board_image
from repositories.game import Game  
import schemas 

from game.init import game_repo

class GameResponseBuilder:
    @staticmethod
    def get_board_state(game: Game):
        image_url, filename = generate_board_image(game.board)
        return schemas.SendMessageResponse(
            result=schemas.Message(
                messageId=uuid.uuid4().hex,
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
            )
        )

    @staticmethod
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
            )
        )

    @staticmethod
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
            )
        )

    @staticmethod
    def handle_move_response(task_id: str, aimove, filename: str, image_url: str):
        return schemas.SendMessageResponse(
            result=schemas.Task(
                id=task_id,
                contextId=str(uuid.uuid4()),
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

    @staticmethod
    def handle_chat_response(text: str):
        return schemas.SendMessageResponse(
            result=schemas.Message(
                messageId=uuid.uuid4().hex,
                role="agent",
                parts=[schemas.TextPart(text=text)],
            )
        )
    
    @staticmethod
    def handle_unknown_command(command_type: str):
        return schemas.SendMessageResponse(
            result=schemas.Message(
                messageId=uuid.uuid4().hex,
                role="agent",
                parts=[
                    schemas.TextPart(
                        text=f"Unknown command type: '{command_type}'. Please try a different command."
                    ),
                ],
            )
        )
