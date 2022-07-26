import click
from convert import *
from export import *
from stats import *

@click.group()
def cli():
    """Convert stuff and statistics"""
    pass


cli.add_command(yt_to_spotify.convert_yt_to_spotify)
cli.add_command(export_spotify_playlist.export_spotify_playlist)
cli.add_command(spotify_playlist_stats.spotify_playlist_stats)
