import os
import pprint
import click
import pickle
from youtube import create_youtube_client
from spotify import create_spotify_client
from time import time


def get_youtube_playlist_items(secrets_file, playlist_id):
    youtube = create_youtube_client.create_youtube_client(secrets_file)
    response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=50,
        playlistId=playlist_id
    ).execute()
    playlistItems = response['items']

    while response.get('nextPageToken'):
        response = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=response['nextPageToken']
        ).execute()
        playlistItems = response['items'] + playlistItems

    return playlistItems


def get_youtube_video(secrets_file, video_id):
    youtube = create_youtube_client.create_youtube_client(secrets_file)
    response = youtube.videos().list(
        part="snippet",
        id=video_id,
        hl="en"
    ).execute()
    return response['items'][0]


@click.command()
@click.option('--secret-file', default="client_secret.json", help="Path to GoogleAPI Credential File")
@click.option('--spotify-client-id', default=os.environ['SPOTIFY_CLIENT_ID'],
              help="Default is SPOTIFY_CLIENT_ID env variable")
@click.option('--spotify-client-secret', default=os.environ['SPOTIFY_CLIENT_SECRET'],
              help="Default is SPOTIFY_CLIENT_SECRET env variable")
@click.argument('playlist_id')
def convert_yt_to_spotify(secret_file, playlist_id, spotify_client_id, spotify_client_secret):
    """
    Takes a youtube playlist and converts it into a spotify one
    Make sure to retrieve spotify and youtube data api credentials
    """

    yt_items = reversed(get_youtube_playlist_items(secret_file, playlist_id))
    spotify_search_queries = []

    # what's regex?
    remove_strings = ['MV', 'Official Music Video', 'Official Video', 'Official Lyric Video',
                      'Official HD Video', 'Official Audio', 'LyricVideo', 'MusicVideo', 'Audio',
                      'Video', 'HD', 'Original Song', 'HQ', 'Color Coded',
                      '()', '[]', '【 】', '（）', '( )', '[ ]', '【  】', '（ ）', 'From', 'Lyrics', '|']
    remove_strings = remove_strings + [remove_string.upper() for remove_string in remove_strings]

    for yt_item in yt_items:
        description = yt_item['snippet']['description']
        if description == "This video is unavailable.": continue

        title = yt_item['snippet']['title']
        if not title.isascii():
            video = get_youtube_video(secret_file, yt_item['snippet']['resourceId']['videoId'])
            if video['snippet']['localized']['title']:
                title = video['snippet']['localized']['title']

        artist = yt_item['snippet']['videoOwnerChannelTitle']

        if description.find("Auto-generated by YouTube.") != -1:
            spotify_search_queries.append(f'{title} - {artist.replace(" - Topic", "")}')
        else:
            for remove_string in remove_strings:
                title = title.replace(remove_string, "")
            spotify_search_queries.append(f'{title}')

    sp = create_spotify_client.create_spotify_client(spotify_client_id, spotify_client_secret)
    for index, query in enumerate(spotify_search_queries):
        if len(query) > 120: query = query[:69]
        response = sp.search(query, type="track")
        try:
            song = response['tracks']['items'][0]
            click.echo(
                f"{index + 1}/{len(spotify_search_queries)} {song['name']} - {song['artists'][0]['name']}               ====              {query}")
        except IndexError:
            # version, remix
            click.echo("     Track not found for " + query)
