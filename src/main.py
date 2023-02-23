import click
from src.convert import *
from src.export import *


@click.group()
def cli():
    """Convert stuff"""
    pass


cli.add_command(yt_to_spotify.convert_yt_to_spotify)
cli.add_command(export_spotify_playlist.export_spotify_playlist)
cli.add_command(apmusic_to_spotify.convert_ap_to_spotify)
