import json
from difflib import SequenceMatcher
from typing import List, Tuple
from pathlib import Path
from urllib.parse import urlparse


def load_json(file: str) -> dict:
    with open(file) as json_file:
        return json.load(json_file)


def get_files_from_dir(directory: str, extension: str) -> List[str]:
    return [str(x.absolute()) for x in Path(directory).glob(f'**/*.{extension}')]


def extract_common_prefix(strings: List[str]) -> str:
    matches = []
    for s in strings[1:]:
        match = SequenceMatcher(None, s, strings[0]).get_matching_blocks()
        matches.append(s[match[0].a:match[0].b + match[0].size])
    return min(matches, key=len)


def parse_s3_url(url: str) -> Tuple[str, str]:
    return urlparse(url).path.split('/')[1], '/'.join(urlparse(url).path.split('/')[2:])


def get_rel_links(metadata: dict, rel: str) -> List[str]:
    return [link.get('href') for link in metadata.get('links') if link.get('rel') == rel]


def unparse_s3_url(s3_url: str, key: str) -> str:
    url = f"{urlparse(s3_url).scheme}://{urlparse(s3_url).hostname}"
    bucket = urlparse(s3_url).path.split('/')[1]
    return f"{url}/{bucket}/{key}"
