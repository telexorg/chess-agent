import schemas
from uuid import uuid4
from repositories.game import GameRepository
from repositories.redis import r as redis_client
from game.move import process_message

game_repo = GameRepository(redis_client)

async def handle_message_send(params: schemas.MessageSendParams):
    task_id = uuid4().hex if not params.message.task_id else params.message.task_id
    user_input = params.message.parts[0].text.strip()

    return await process_message(task_id, user_input)

async def handle_get_task(params: schemas.TaskQueryParams):
    task_state = game_repo.task_state(params.id)

    response = schemas.GetTaskResponse(
        result=schemas.Task(
            id=params.id,
            status=schemas.TaskStatus(
                state=task_state,
                message=schemas.Message(
                    messageId=uuid4().hex,
                    role="agent",
                    parts=[
                        schemas.TextPart(text=f"The current task state is {task_state}"),
                    ],
                ),
            ),
        ),
    )

    return response
