import base64
import json
import requests
import sys
from typing import TypedDict

from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript


class SubtitleNotAvailable(Exception):
    """Exception raised for errors in the input."""


class CaptionData(TypedDict):
    text: str
    start: int  # ms
    duration: int  # ms


def retrieve(video_id: str, lang="en") -> list[CaptionData]:
    try:
        items = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        return [
            {
                "text": item["text"],
                "start": int(item["start"] * 1000),
                "duration": int(item["duration"] * 1000),
            }
            for item in items
        ]
    except CouldNotRetrieveTranscript as e:
        raise SubtitleNotAvailable(str(e))


# https://stackoverflow.com/questions/69937867/google-video-no-longer-able-to-retrieve-captions/70013529#70013529
def retrieve2(video_id: str, lang="en"):
    base64_lang = (
        base64.b64encode(("\n\x00\x12\x02%s\x1a\x00" % lang).encode())
        .decode()
        .replace("=", "%3D")
    )
    print(base64_lang)

    base64_bytes = base64.b64encode(
        ("\n\v" + video_id + "\x12\x0e" + base64_lang).encode("utf-8")
    )
    headers = {
        "Content-Type": "application/json",
    }

    body = json.dumps(
        {
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.9999099"}},
            "params": base64_bytes.decode("utf-8"),
        }
    )
    print(base64_bytes.decode("utf-8"))
    response = requests.post(
        "https://www.youtube.com/youtubei/v1/get_transcript?key=YOUTUBE_API_KEY",
        headers=headers,
        data=body,
    )

    return response.text


if __name__ == "__main__":
    VIDEO_ID = sys.argv[1] if len(sys.argv) >= 2 else "yVV08GZ7sm0"
    LANG = sys.argv[2] if len(sys.argv) >= 3 else "ja"
    # txt = retrieve2(VIDEO_ID, LANG)
    captions = retrieve(VIDEO_ID, languages=[LANG])
    with open("captions/%s.json" % VIDEO_ID, "w") as fs:
        fs.write(json.dumps(captions, indent=4, ensure_ascii=False))
