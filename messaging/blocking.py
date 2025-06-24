import a2a
from uuid import uuid4
from repositories.game import GameRepository
from repositories.redis import r as redis_client
from repositories.env import CHESS_ENGINE_PATH
from game.move import (
    handle_final_response,
    handle_resignation,
    handle_user_move_as_board,
    handle_game_over,
)
from game.utils import generate_board_image

game_repo = GameRepository(redis_client)


async def handle_message_send(params: a2a.MessageSendParams):
    task_id = uuid4().hex if not params.message.taskId else params.message.taskId
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
            messageId=uuid4().hex,
            error=a2a.InvalidParamsError(
                message=f"Invalid move: '{user_move}'",
                data=f"You sent '{user_move}' which is not a valid chess move",
            ),
        )
        return response
    except:
        response = a2a.JSONRPCResponse(
            messageId=uuid4().hex,
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
                    messageId=uuid4().hex,
                    role="agent",
                    parts=[
                        a2a.TextPart(text=f"The current task state is {task_state}"),
                    ],
                ),
            ),
        ),
    )

    return response
