import click
from json import load


@click.command()
@click.argument(playlist_id)
def spotify_playlist_stats(playlist_id):
    with open(f"{playlist_id}-spotify-tracks.json", "r") as infile:
        tracks = json.load(infile)
