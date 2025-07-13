from repositories.game import Game
from game.utils import generate_board_image
from repositories.env import CHESS_ENGINE_PATH
from repositories.game import ChessCommandResponse
from game.command_processor import CommandProcessor


from game.init import game_repo
from game.responses import GameResponseBuilder 

def load_or_start_game(task_id: str):
    game = game_repo.load(task_id)
    if not game:
        game = game_repo.start_game(engine_path=CHESS_ENGINE_PATH)
    return game


def process_user_move(game: Game, command_response: ChessCommandResponse, task_id: str):
    command_processor = CommandProcessor()

    return command_processor.process(game=game, command_response=command_response, task_id=task_id)


async def process_message(task_id: str, user_input: str):
    game = load_or_start_game(task_id)
    command_response = await game_repo.parse_command(user_input, game)

    print(f"Command response is {command_response}")

    if command_response.command_type == "chat":
        return GameResponseBuilder.handle_chat_response(command_response.chat_query_response)
    
    if command_response.command_type == "board":
        return GameResponseBuilder.get_board_state(game)
    
    if command_response.command_type == "resign":
        return GameResponseBuilder.handle_resignation(task_id)
    
    if command_response.command_type == "unknown":
        return GameResponseBuilder.handle_chat_response(command_response.message)

    if command_response.command_type == "move":
        error_response = process_user_move(game, command_response, task_id)
        if error_response:
            return error_response
        
        aimove, board = game.aimove()
        game_repo.save(task_id, game)

        image_url, filename = generate_board_image(board)

        if board.is_game_over():
            return GameResponseBuilder.handle_game_over(task_id, aimove, filename, image_url)

        return GameResponseBuilder.handle_move_response(task_id, aimove, filename, image_url)
    
    return GameResponseBuilder.handle_unknown_command(command_response.command_type)
