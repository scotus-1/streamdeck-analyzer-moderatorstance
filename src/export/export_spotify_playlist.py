import click
import os
from json import dump
from spotify import create_spotify_client


@click.command()
@click.option('--spotify-client-id', default=os.environ['SPOTIFY_CLIENT_ID'],
              help="Default is SPOTIFY_CLIENT_ID env variable")
@click.option('--spotify-client-secret', default=os.environ['SPOTIFY_CLIENT_SECRET'],
              help="Default is SPOTIFY_CLIENT_SECRET env variable")
@click.argument('playlist_id')
def export_spotify_playlist(playlist_id, spotify_client_id, spotify_client_secret):
    """
    Exports spotify playlist items metadata to json
    """
    sp = create_spotify_client.create_spotify_client(spotify_client_id, spotify_client_secret)
    user_id = sp.me()['id']

    playlist = sp.playlist(playlist_id)
    response = sp.user_playlist_tracks(user_id, playlist_id, limit=50)
    tracks = response['items']
    while response['next']:
        response = sp.user_playlist_tracks(user_id, playlist_id, limit=50, offset=response['offset'] + 50)
        tracks += response['items']

    with open(f'{playlist["id"]}-spotify-tracks.json', 'w') as output_file:
        dump(tracks, output_file, indent=4)
