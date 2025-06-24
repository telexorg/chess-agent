from repositories.random_name import RandomNameRepository
from repositories.env import MINIO_BUCKET_NAME
from repositories.minio import minio_client


def generate_board_image(board):
    filename = RandomNameRepository.generate_filename()
    destination_file = f"public/chessagent/{filename}"
    source_file = f"/tmp/{filename}"

    svg = board._repr_svg_()

    with open(source_file, "w") as f:
        f.write(svg)
        new_source_file = source_file.split(".svg")[0] + ".png"

        import cairosvg

        cairosvg.svg2png(url=source_file, write_to=new_source_file)

        source_file = new_source_file
        destination_file = destination_file.split(".svg")[0] + ".png"

    minio_client.fput_object(
        MINIO_BUCKET_NAME,
        destination_file,
        source_file,
    )

    image_url = f"https://media.tifi.tv/{MINIO_BUCKET_NAME}/{destination_file}"

    return image_url, filename
