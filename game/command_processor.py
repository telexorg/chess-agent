import schemas
from uuid import uuid4
from repositories.game import Game
from repositories.game import ChessCommandResponse
from game.responses import GameResponseBuilder

def build_error_response(message: str, data: str | None = None):
    return schemas.JSONRPCResponse(
        messageId=uuid4().hex,
        error=schemas.InvalidParamsError(message=message, data=data),
    )


class CommandProcessor:
    def __init__(self):
        self.handlers = {
            "board": self._handle_board,
            "resign": self._handle_resign,
            "move": self._handle_move,
            "invalid": self._handle_invalid,
            "analysis": self._handle_analysis,
            "hint": self._handle_hint,
        }

    def process(self, *, game: Game, command_response: ChessCommandResponse, task_id: str):
        handler = self.handlers.get(command_response.command_type)
        if not handler:
            return build_error_response(
                "Unknown command",
                f"Command '{command_response.command_type}' not supported",
            )

        return handler(game=game, command_response=command_response, task_id=task_id)

    def _handle_board(self, *, game: Game, **kwargs):
        return GameResponseBuilder.get_board_state(game)

    def _handle_resign(self, *, task_id: str, **kwargs):
        return GameResponseBuilder.handle_resignation(task_id)

    def _handle_move(self, *, game: Game, command_response: ChessCommandResponse, **kwargs):
        if not command_response.move:
            return build_error_response(
                "No move provided", "Move command requires a chess move"
            )

        try:
            game.usermove(command_response.move)
            return None  # Success case
        except ValueError:
            return build_error_response(
                f"Invalid move: '{command_response.move}'",
                f"'{command_response.move}' is not a valid chess move",
            )
        except Exception:
            return build_error_response("An error occurred while processing your move")

    def _handle_invalid(self, *, command_response: ChessCommandResponse, **kwargs):
        return build_error_response(
            "Invalid command",
            command_response.error_message or "Command not recognized",
        )

    def _handle_analysis(self, **kwargs):
        return build_error_response("Not implemented", "Analysis feature is coming soon.")

    def _handle_hint(self, **kwargs):
        return build_error_response("Not implemented", "Hint feature is coming soon.")



