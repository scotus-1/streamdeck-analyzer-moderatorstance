import click


@click.group()
def cli():
    """Example script."""
    pass


cli.add_command()
