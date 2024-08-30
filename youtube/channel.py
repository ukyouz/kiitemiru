#!/usr/bin/python

# This sample executes a search request for the specified search term.
# Sample usage:
#   python search.py --q=surfing --max-results=10
# NOTE: To use the sample, you must provide a developer key obtained
#       in the Google APIs Console. Search for "REPLACE_ME" in this code
#       to find the correct place to provide that key..

import argparse
import json
import os
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError

import certifi
from dotenv import load_dotenv

load_dotenv()

# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError


# # Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# # tab of
# #   https://cloud.google.com/console
# # Please ensure that you have enabled the YouTube Data API for your project.
# DEVELOPER_KEY = "YOUTUBE_API_KEY"
# YOUTUBE_API_SERVICE_NAME = "youtube"
# YOUTUBE_API_VERSION = "v3"


# def youtube_search(q: str, max_results: int = 25):
#     youtube = build(
#         YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY
#     )

#     # Call the search.list method to retrieve results matching the specified
#     # query term.
#     search_response = (
#         youtube.search().list(q=q, part="id,snippet", maxResults=max_results).execute()
#     )

#     videos = []
#     channels = []
#     playlists = []

#     # Add each result to the appropriate list, and then display the lists of
#     # matching videos, channels, and playlists.
#     for search_result in search_response.get("items", []):
#         if search_result["id"]["kind"] == "youtube#video":
#             videos.append(
#                 "%s (%s)"
#                 % (search_result["snippet"]["title"], search_result["id"]["videoId"])
#             )
#         elif search_result["id"]["kind"] == "youtube#channel":
#             channels.append(
#                 "%s (%s)"
#                 % (search_result["snippet"]["title"], search_result["id"]["channelId"])
#             )
#         elif search_result["id"]["kind"] == "youtube#playlist":
#             playlists.append(
#                 "%s (%s)"
#                 % (search_result["snippet"]["title"], search_result["id"]["playlistId"])
#             )

#     print("Videos:\n", "\n".join(videos), "\n")
#     print("Channels:\n", "\n".join(channels), "\n")
#     print("Playlists:\n", "\n".join(playlists), "\n")


os.environ["SSL_CERT_FILE"] = certifi.where()
YT_API_KEY = os.getenv("YT_API_KEY")


def get_youtube_api_url(endpoint: str, queries: list[str] = None) -> str:
    queries = queries or queries
    queries.append(
        f"key={YT_API_KEY}",
    )
    query = "&".join(queries)
    return f"https://www.googleapis.com/youtube/v3/{endpoint}?{query}"


def get_youtube_api_data(endpoint: str, queries: list[str] = None) -> dict | None:
    url = get_youtube_api_url(endpoint, queries)
    try:
        inp = request.urlopen(url)
    except HTTPError as e:
        print(f"HTTP_ERROR({e.code}): /{endpoint} {e.reason}")
        return None
    except URLError as e:
        print(f"URL_ERROR({e.reason}): /{endpoint}")
        return None
    else:
        return json.load(inp)


def get_channel_info(channel_id: str) -> dict | None:
    resp = get_youtube_api_data(
        "channels",
        [
            "id={}".format(channel_id),
            "part=snippet",
        ],
    )
    if resp and (items := resp["items"]):
        return items[0]
    else:
        return None


def list_videos_for_channel(channel_id, max_count=0, until_date: str = None):
    first_param = [
        "channelId={}".format(channel_id),
        "maxResults={}".format(min(50, max_count or 50)),
        "part=snippet,id",
        "order=date",
        "type=video",
    ]
    items = []
    param = first_param
    fetch_end = False
    while max_count == 0 or len(items) <= max_count:
        """get video snippets"""
        snippets = get_youtube_api_data(
            "search",
            param,
        )
        if snippets is None:
            break

        _temps = []
        for item in snippets["items"]:
            if until_date and item["snippet"]["publishedAt"] <= until_date:
                fetch_end = True
                break

            _temps.append(item)

        if not _temps:
            break

        """get video details"""
        vids = [i["id"]["videoId"] for i in _temps]
        details = get_youtube_api_data(
            "videos",
            [
                "id={}".format(",".join(vids)),
                "part=contentDetails",
            ],
        )
        if details is None:
            break

        """merge snippets and details"""
        assert len(_temps) == len(details["items"])
        for _tmp, detail in zip(_temps, details["items"]):
            assert _tmp["id"]["videoId"] == detail["id"]
            _tmp["contentDetails"] = detail["contentDetails"]

        items.extend(_temps)

        if fetch_end:
            break

        try:
            next_page_token = snippets["nextPageToken"]
        except KeyError:
            break
        print(next_page_token)
        param = first_param + [f"pageToken={next_page_token}"]

    # reverse the order, so that the latest video is at the end
    return items[::-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", help="Search term", default="Google")
    parser.add_argument("--max-results", help="Max results", default=25)
    args = parser.parse_args()

    try:
        youtube_search(args.q, args.max_results)
    except HTTPError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
