import random

class RandomNameRepository:
    WORDS = [
        "sun", "moon", "tree", "cloud", "river", "stone", "eagle", "wolf", "fire",
        "wind", "storm", "leaf", "sky", "night", "light", "shadow", "mountain",
        "ocean", "echo", "whisper", "flame", "dust", "branch",
    ]

    @classmethod
    def generate_filename(cls, extension: str = "svg", word_count: int = 3) -> str:
        words = random.sample(cls.WORDS, word_count)
        return "_".join(words) + f".{extension}"

    @classmethod
    def generate_suffix(cls, word_count: int = 2) -> str:
        return "_".join(random.sample(cls.WORDS, word_count))
