import os
import pprint
import click
import lxml
import bs4
from src.spotify import create_spotify_client


def get_apple_music_playlist_items(html_file):
    with open(html_file, 'r', encoding="utf-8") as out_f:
        soup = bs4.BeautifulSoup(out_f, 'lxml')
        rows = soup.find_all("div", class_="songs-list-row")
        songs = []
        for row in rows:
            song = row.find("div", class_="songs-list__col--song").find("div", class_="songs-list-row__song-name").text
            artist = row.find("div", class_="songs-list__col--secondary").find("span").text
            songs.append(
                {
                    "song": song,
                    "artist": artist
                }
            )

        return songs


def get_apple_music_playlist_title(html_file):
    with open(html_file, 'r', encoding="utf-8") as out_f:
        soup = bs4.BeautifulSoup(out_f, 'lxml')
        title = soup.find("h1").text
        return title


@click.command()
@click.option('--spotify-client-id', default=os.environ['SPOTIFY_CLIENT_ID'],
              help="Default is SPOTIFY_CLIENT_ID env variable")
@click.option('--spotify-client-secret', default=os.environ['SPOTIFY_CLIENT_SECRET'],
              help="Default is SPOTIFY_CLIENT_SECRET env variable")
@click.argument('html_file')
def convert_ap_to_spotify(html_file, spotify_client_id, spotify_client_secret):
    """
    Takes an apple music playlist (from an html or htm file) and converts it into a spotify one
    Make sure to retrieve spotify api credentials
    """
    click.echo("")
    click.echo("Getting Apple Music playlist items     ------------")
    ap_items = get_apple_music_playlist_items(html_file)

    songs = []
    not_found_songs = []
    sp = create_spotify_client.create_spotify_client(spotify_client_id, spotify_client_secret)
    with click.progressbar(length=len(ap_items), label="Searching on Spotify",
                           item_show_func=lambda q: q) as bar:
        for index, ap_item in enumerate(ap_items):
            song_name = ap_item['song']
            flag_strings = ['feat.', 'ft.', 'with', 'from', 'remaster', 'bonus', 'single', "radio", "interlude",
                            "enterlude", "mixed"]

            flag_strings += [flag_string.upper() for flag_string in flag_strings]
            flag_strings += [flag_string.capitalize() for flag_string in flag_strings]

            for flag_string in flag_strings:
                first_parenthesis = song_name.find("(")
                second_parenthesis = song_name.find(")")
                first_bracket = song_name.find("[")
                second_bracket = song_name.find("]")

                if not -1 in (first_parenthesis, second_parenthesis):
                    if flag_string in song_name[first_parenthesis + 1:second_parenthesis]:
                        song_name = song_name[:song_name.find("(")] + song_name[song_name.find(")") + 1:]
                        break

                if not -1 in (first_bracket, second_bracket):
                    if flag_string in song_name[first_bracket + 1:second_bracket]:
                        song_name = song_name[:first_bracket] + song_name[second_bracket + 1:]
                        break

            bad_characters = ["'", '"', ":", "&", "?"]
            for bad_character in bad_characters:
                song_name = song_name.replace(bad_character, "")

            if len(song_name) > 120: song_name = song_name[:69]

            artist_name = ap_item['artist']
            bad_characters = ["'", '"', ":", "!"]
            for bad_character in bad_characters:
                artist_name = artist_name.replace(bad_character, "")

            if not artist_name.find("&") == -1:
                artist_name = artist_name[:artist_name.find("&")]
            if not artist_name.find(",") == -1:
                artist_name = artist_name[:artist_name.find(",")]

            query = f"track:{song_name.strip()} artist:{artist_name}"
            response = sp.search(query, type="track", limit=9)
            try:
                song = response['tracks']['items'][0]
                song['query'] = query
                song['other_results'] = response['tracks']['items']
                songs.append(song)

                bar.update(1,
                           f"{index + 1}/{len(ap_items)} {song['name']} - {song['artists'][0]['name']}               ====              {query}")
            except IndexError:
                not_found_songs.append({"query": query, })
                bar.update(1, "     Track not found for " + query)

    click.echo("===================================================================")
    click.echo(f"Found {len(songs)}/{len(ap_items)}")
    not_added_songs = []
    marked_for_removal = []
    for not_found_song in not_found_songs:
        click.echo(f"Did not find: {not_found_song['query']}")

        if click.confirm("Would you like to search for this song?", default=True):
            query = click.prompt(
                "Input your manuel search query here (Try either a simpler query or a different version)", type=str)
            searched_songs = sp.search(query, type="track", limit=9)['tracks']['items']

            for index, searched_song in enumerate(searched_songs):
                click.echo(
                    f"[{index}] {searched_song['name']} - {searched_song['artists'][0]['name']} - {searched_song['album']['name']}")

            click.echo(f"[{len(searched_songs)}] Completely Ignore and log")
            option = click.prompt("Input option number", type=int, default=0)

            if not option == len(searched_songs):
                chosen_song = searched_songs[option]
                chosen_song['query'] = not_found_song['query']
                songs.append(chosen_song)
                marked_for_removal.append(not_found_song)
            click.echo("\n")

    for marked in marked_for_removal:
        not_found_songs.remove(marked)

    click.echo("\n")
    if not click.confirm("Final Review Process (go through each song) skip?", default=False):
        current_song_index = 0
        selection_amount = 5

        while True:
            click.clear()
            current_selection = songs[current_song_index - selection_amount:current_song_index + selection_amount + 1]
            for index, song in enumerate(current_selection):
                song_index = current_song_index - selection_amount + index
                if index < selection_amount or index > selection_amount:
                    click.echo(
                        f"{song_index + 1}/{len(songs)} {song['name']} - {song['artists'][0]['name']}               ====              {song['query']}")
                else:
                    click.echo(
                        f"\n ======= {song_index + 1}/{len(songs)} {song['name']} - {song['artists'][0]['name']}               ====              {song['query']}\n")

            click.echo("\nControls: h for up, j or ENTER for down, m for more options")
            song = songs[current_song_index]
            user_input = click.prompt(
                f"\n{current_song_index + 1}/{len(songs)} {song['name']} | {song['artists'][0]['name']} | {song['album']['name']} - review?",
                default='j', type=click.Choice(['h', 'j', 'm'], case_sensitive=False), show_choices=True)
            if user_input == "m":
                query = click.prompt(
                    "Input your manuel search query here (Try either a simpler query or a different version)", type=str)
                searched_songs = sp.search(query, type="track", limit=9)['tracks']['items']

                for i, searched_song in enumerate(searched_songs):
                    click.echo(
                        f"[{i}] {searched_song['name']} - {searched_song['artists'][0]['name']} - {searched_song['album']['name']}")

                click.echo(f"[{len(searched_songs)}] Completely Ignore and log")
                option = click.prompt("Input option number", type=int, default=0)

                if option == len(searched_songs):
                    songs.remove(song)
                    not_added_songs.append(song)
                else:
                    i = songs.index(song)
                    chosen_song = searched_songs[option]
                    chosen_song['query'] = song['query']
                    songs = songs[:i] + [chosen_song] + songs[i + 1:]
                click.echo("\n")
            elif user_input == "h":
                current_song_index -= 1
            elif user_input == "j":
                if current_song_index == len(songs) - 1:
                    if click.confirm("Are these your final results?", default=False):
                        break
                    else:
                        continue
                else:
                    current_song_index += 1

    click.echo("\n===============================")
    click.echo("Creating Spotify Playlist...")
    ap_title = get_apple_music_playlist_title(html_file)
    user_id = sp.me()['id']
    sp_playlist = sp.user_playlist_create(user_id, ap_title, False, False,
                                          f"funee monkey smile: {ap_title}")
    song_ids = [song['id'] for song in songs]

    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    with click.progressbar(length=len(songs), label="Adding to Spotify Playlist") as bar:
        for chunk in chunker(song_ids, 100):
            sp.user_playlist_add_tracks(user_id, sp_playlist['id'], chunk)
            bar.update(len(chunk))

    click.echo("\n===============================")
    for not_added_song in not_added_songs:
        click.echo(
            f"Permanently Removed: {not_added_song['name']} - {not_added_song['artists'][0]['name']} | {not_added_song['query']}")

    click.echo("\n")
    for not_found_song in not_found_songs:
        click.echo(
            f"Did not find: {not_found_song['query']}")
