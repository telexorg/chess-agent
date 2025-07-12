import os
import schemas
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse
from repositories.env import DEPLOYMENT_TYPE, DeploymentTypes, PORT
from messaging.webhook import handle_message_send_with_webhook
from messaging.blocking import handle_message_send, handle_get_task
from agent_details.card import get_agent_card
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def read_root():
    return '<p style="font-size:40px">Chess bot A2A</p>'

@app.post("/")
async def handle_rpc(request_data: dict, background_tasks: BackgroundTasks):
    try:
        rpc_request = schemas.A2ARequest.validate_python(request_data)

        if isinstance(rpc_request, schemas.SendMessageRequest):
            print("Recieved message/send")
            if DEPLOYMENT_TYPE == DeploymentTypes.BLOCKING.value:
                print("handling blocking mode")
                return await handle_message_send(params=rpc_request.params)
            elif DEPLOYMENT_TYPE == DeploymentTypes.STREAMING.value:
                print("handling streaming mode")
                pass
            elif DEPLOYMENT_TYPE == DeploymentTypes.WEBHOOK.value:
                print("handling webhooks mode")
                return await handle_message_send_with_webhook(
                    params=rpc_request.params, background_tasks=background_tasks
                )
            else:
                print("defaulting to blocking mode")
                return await handle_message_send(params=rpc_request.params)
        elif isinstance(rpc_request, schemas.GetTaskRequest):
            print("tasks/get")
            return await handle_get_task(params=rpc_request.params)
        else:
            raise HTTPException(status_code=400, detail="Method not supported")

    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=400, detail="Could not handle task")


@app.get("/.well-known/agent.json")
def agent_card(request: Request):
    BASE_URL = os.getenv("BASE_URL")
    external_base = request.headers.get("x-external-base-url", "")
    base_url = BASE_URL if BASE_URL else (str(request.base_url).rstrip("/") + external_base)

    return get_agent_card(base_url)

@app.get("/telex-extensions")
def telex_extensions():
    return {
        "isPaid": True
    }

if __name__ == "__main__":
    import uvicorn

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = os.getenv("PORT", 7000)
    SHOULD_RELOAD = bool(os.getenv("SHOULD_RELOAD", 0))

    uvicorn.run("main:app", host=HOST, port=PORT, reload=SHOULD_RELOAD)
