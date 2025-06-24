import os
import a2a
from repositories.random_name import RandomNameRepository
from repositories.env import WITH_TELEX_EXTENSIONS

agent_name_suffix = (
    "_" + os.getenv("APP_ENV") + "_" + RandomNameRepository.generate_suffix()
    if os.getenv("APP_ENV") == "local"
    else ""
)


def get_agent_card(base_url):
    card = a2a.AgentCard(
        name=f"Chess Agent{agent_name_suffix}",
        description="An agent that plays chess. Accepts moves in standard notation and returns updated board state as FEN and an image.",
        url=f"{base_url}",
        provider=a2a.AgentProvider(
            organization="Telex",
            url="https://www.telex.im",
        ),
        version="1.0.0",
        documentationUrl=f"{base_url}/docs",
        capabilities=a2a.AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=True,
        ),
        authentication=a2a.AgentAuthentication(schemes=["Bearer"]),
        defaultInputModes=["text/plain"],
        defaultOutputModes=["application/x-fen", "image/png"],
        skills=[
            a2a.AgentSkill(
                id="play_move",
                name="Play Move",
                description="Plays a move and returns the updated board in FEN format and as an image.",
                tags=["chess", "gameplay", "board"],
                examples=["e4", "Nf3", "d5"],
                inputModes=["text/plain"],
                outputModes=["application/x-fen", "image/png"],
            ),
        ],
    )

    telex_skill = a2a.AgentSkill(
        id="telex-extensions",
        name="Telex Extensions",
        description="This agent supports extra features offered by the telex platform.",
        tags=["telex", "telex-extensions"],
    )

    if WITH_TELEX_EXTENSIONS:
        card.skills.append(telex_skill)

    return card
