import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import pickle
from time import time


def build_youtube_client(secrets_file):
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=flow.run_console())

    with open('./youtubeapiclient.pkl', 'wb') as outp:
        youtube.timestamp = time()
        pickle.dump(youtube, outp, pickle.HIGHEST_PROTOCOL)

    return youtube


def create_youtube_client(secrets_file):
    if os.path.exists("./youtubeapiclient.pkl"):
        with open("./youtubeapiclient.pkl", "rb") as inp:
            obj = pickle.load(inp)
            if obj.timestamp + 518400 > time():
                return obj
            else:
                return build_youtube_client(secrets_file)
    else:
        return build_youtube_client(secrets_file)
