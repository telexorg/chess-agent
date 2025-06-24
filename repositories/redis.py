import redis
from dataclasses import dataclass

@dataclass
class RedisKeys:
    games = "games"

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
