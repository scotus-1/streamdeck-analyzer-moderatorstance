import click
from convert import *



@click.group()
def cli():
    """Convert stuff and statistics"""
    pass

cli.add_command(yt_to_spotify.convert_yt_to_spotify)
