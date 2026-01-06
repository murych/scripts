import logging
from pathlib import Path
from argparse import ArgumentParser
from typing import Generator
from mutagen.id3 import Encoding, ID3, ID3NoHeaderError
from mutagen import MutagenError

tags_to_modify = ["TIT2", "TALB", "TPE1"]


def find_files(root: Path, extension: str = ".mp3") -> Generator[Path, None, None]:
    if not extension.startswith("."):
        extension = "." + extension
    for path in root.rglob(f"*{extension}"):
        if path.is_file():
            yield path


def convert_encs(tag: ID3) -> str:
    if tag.encoding != Encoding.LATIN1:
        raise EncodingWarning
    if not tag.text:
        raise IndexError
    try:
        return tag.text[0].encode("iso-8859-1").decode("cp1251")
    except UnicodeEncodeError as e:
        raise e


def main() -> int:
    parser = ArgumentParser("mp3 tag encoding fix")
    parser.add_argument("path", type=str, default=".")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--from")
    parser.add_argument("--to")
    args = parser.parse_args()

    logger = logging.getLogger("encoding_fix")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    logger.addHandler(ch)

    root = Path(args.path)
    if not root.exists() or root.is_file():
        logger.error(f"path {root} does not exist or is a file")
        return 1

    for file in find_files(root=root, extension=".mp3"):
        logger.info(f"PROCESSING FILE {file}")
        try:
            id3 = ID3(file)
        except ID3NoHeaderError:
            logger.warning("\tPASS: Cant open file id3")
            continue

        for tag in tags_to_modify:
            tags = id3.getall(tag)
            if not tags:
                logger.debug(f"\tPASS: NO TAGS {tag} found")
                continue

            try:
                decoded = convert_encs(tags[0])
                logger.debug(f"\tprocessed tag {tag}, converted: {decoded}")
            except EncodingWarning or UnicodeEncodeError:
                logger.warning(f"\tPASS tag {tag}, will not convert {file.name}")
                continue
            except IndexError:
                logger.warning(f"\tPASS w {tag}, NO TAGS: {file.name}")
                continue
            if decoded is None:
                pass
            else:
                tags[0].text = decoded
                tags[0].encoding = Encoding.UTF8

        try:
            id3.save()
            logger.info(f"PROCESSED FILE {file.name} OK\n")
        except MutagenError as e:
            logger.error(f"error occured while saving file {file.name}: {e}\n")

    return 0


if __name__ == "__main__":
    ret = main()
    exit(ret)
