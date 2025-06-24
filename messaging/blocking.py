import a2a
from uuid import uuid4
from repositories.game import GameRepository
from repositories.redis import r as redis_client
from game.move import process_message

game_repo = GameRepository(redis_client)

async def handle_message_send(params: a2a.MessageSendParams):
    task_id = uuid4().hex if not params.message.taskId else params.message.taskId
    user_input = params.message.parts[0].text.strip()
    
    return await process_message(task_id, user_input)

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
