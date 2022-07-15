import os
import pprint
import click
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from time import time


def create_youtube_client(secrets_file):
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=flow.run_console())

    if not os.path.exists('./.cache'):
        os.mkdir('./.cache')
    with open('./.cache/youtubeapiclient.pkl', 'wb') as outp:
        youtube.timestamp = time()
        pickle.dump(youtube, outp, pickle.HIGHEST_PROTOCOL)

    return youtube


def get_youtube_playlist_items(secrets_file, playlist_id):
    if os.path.exists("./.cache/youtubeapiclient.pkl"):
        with open("./.cache/youtubeapiclient.pkl", "rb") as inp:
            obj = pickle.load(inp)
            if obj.timestamp + 518400 > time():
                youtube = obj
            else: youtube = create_youtube_client(secrets_file)
    else: youtube = create_youtube_client(secrets_file)


    response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=50,
        playlistId=playlist_id
    ).execute()
    playlistItems = response['items']

    while response.get('nextPageToken'):
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=response['nextPageToken']
        ).execute()
        playlistItems = response['items'] + playlistItems

    return playlistItems


@click.command()
@click.option('--secret-file', default="client_secret.json", help="Path to GoogleAPI Credential File")
@click.argument('playlist_id')
def convert_yt_to_spotify(secret_file, playlist_id):
    yt_items = get_youtube_playlist_items(secret_file, playlist_id)
    spotify_search_queries = []
    print(len(yt_items))
    # if official audio, search query for spotify would be channel name + song name
    # else use video title with stripped info