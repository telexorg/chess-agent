import schemas
from typing import Any
from fastapi import BackgroundTasks
from uuid import uuid4
import httpx
from repositories.game import GameRepository
from repositories.redis import r as redis_client
from game.move import process_message
from helpers.utils import safe_get

game_repo = GameRepository(redis_client)

async def actual_messaging(params: schemas.MessageSendParams, task_id:str, webhook_url: str, auth_headers: dict[str, Any]):
    user_input = params.message.parts[0].text.strip()
    response = await process_message(task_id, user_input)

    res = httpx.post(webhook_url, headers=auth_headers, json=response.model_dump())
    if res.status_code < 300:
        print("Succeeded in webhook response")
    else:
        print(f"Failed to send webhook response: status - {res.status_code} body - {res.text}")


async def handle_message_send_with_webhook(params: schemas.MessageSendParams, background_tasks: BackgroundTasks):
    webhook_url = safe_get(params, "configuration", "pushNotificationConfig", "url")
    scheme = safe_get(params, "configuration", "pushNotificationConfig", "authentication", "schemes")
    credential = safe_get(params, "configuration", "pushNotificationConfig", "authentication", "credentials")

    auth_headers = {}

    if "TelexApiKey" in scheme:
        auth_headers["X-TELEX-API-KEY"] = credential

    if not webhook_url:
        return schemas.JSONRPCResponse(
            messageId=uuid4().hex,
            error=schemas.InvalidParamsError(
                message="No webhook URL provided, but is necessary",
            ),
        )
    
    existing_task_id = params.message.task_id
    task_id = existing_task_id if existing_task_id else uuid4().hex

    background_tasks.add_task(actual_messaging, params, task_id, webhook_url, auth_headers)


    return schemas.SendMessageResponse(
        result=schemas.Task(
            id=task_id,
            status=schemas.TaskStatus(
                state=schemas.TaskState.working
            )
        ),
    )
