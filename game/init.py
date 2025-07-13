from repositories.redis import r as redis_client
from repositories.game import GameRepository

game_repo = GameRepository(redis_client)
