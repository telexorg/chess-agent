import a2a
from typing import Any
from fastapi import BackgroundTasks
from uuid import uuid4
import httpx
from repositories.game import GameRepository
from repositories.redis import r as redis_client
from repositories.env import CHESS_ENGINE_PATH
from game.move import handle_final_response
from game.utils import generate_board_image
from helpers.utils import safe_get

game_repo = GameRepository(redis_client)

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
            messageId=uuid4().hex,
            error=a2a.InvalidParamsError(
                message=f"Invalid move: '{user_move}'",
                data=f"You sent '{user_move}' which is not a valid chess move",
            ),
        )
        
    except:
        error_response = a2a.JSONRPCResponse(
            messageId=uuid4().hex,
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
            messageId=uuid4().hex,
            error=a2a.InvalidParamsError(
                message="No webhook URL provided, but is necessary",
            ),
        )
    
    existing_task_id = params.message.taskId
    task_id = existing_task_id if existing_task_id else uuid4().hex

    background_tasks.add_task(actual_messaging, params, task_id, webhook_url, auth_headers)


    return a2a.SendMessageResponse(
        result=a2a.Task(
            id=task_id,
            status=a2a.TaskStatus(
                state=a2a.TaskState.working
            )
        ),
    )
