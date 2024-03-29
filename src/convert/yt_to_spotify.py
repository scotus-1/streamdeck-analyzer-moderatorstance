import os
import pprint
import click
import pickle
import urllib.parse
from src.youtube import create_youtube_client
from src.spotify import create_spotify_client


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


def get_youtube_playlist(secrets_file, playlist_id):
    youtube = create_youtube_client.create_youtube_client(secrets_file)
    response = youtube.playlists().list(
        part="snippet",
        id=playlist_id
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
    click.echo("")
    click.echo("Getting YouTube playlist items     ------------")
    yt_items = list(reversed(get_youtube_playlist_items(secret_file, playlist_id)))
    spotify_search_queries = []

    # what's regex?
    remove_strings = ['MV', 'Official Music Video', 'Official Video', 'Official Lyric Video',
                      'Official HD Video', 'Official Audio', 'LyricVideo', 'MusicVideo', 'Audio',
                      'Video', 'HD', 'Original Song', 'HQ', 'Color Coded',
                      '()', '[]', '【 】', '（）', '( )', '[ ]', '【  】', '（ ）', 'From', 'Lyrics', '|'
                                                                                              '「 ', '」', '『 ', '』', '【',
                      '】']
    remove_strings += [remove_string.upper() for remove_string in remove_strings]

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
    songs = []
    flagged_songs = []
    not_found_songs = []
    flag_strings = ['version', 'remix', 'instrumental', 'ver.']
    flag_strings += [flag_string.upper() for flag_string in flag_strings]
    flag_strings += [flag_string.capitalize() for flag_string in flag_strings]
    with click.progressbar(length=len(spotify_search_queries), label="Searching on Spotify",
                           item_show_func=lambda q: q) as bar:
        for index, query in enumerate(spotify_search_queries):
            if len(query) > 120: query = query[:69]
            response = sp.search(query, type="track", limit=9)
            try:
                song = response['tracks']['items'][0]
                song['query'] = query
                song['other_results'] = response['tracks']['items']
                song['youtube_id'] = yt_items[index]['snippet']['resourceId']['videoId']
                songs.append(song)
                for flag_string in flag_strings:
                    if flag_string in song['name']:
                        flagged_songs.append(song)
                        break
                bar.update(1,
                           f"{index + 1}/{len(spotify_search_queries)} {song['name']} - {song['artists'][0]['name']}               ====              {query}")
            except IndexError:
                not_found_songs.append(
                    {
                        "query": query,
                        "youtube_id": yt_items[index]['snippet']['resourceId']['videoId']
                    }
                )
                bar.update(1, "     Track not found for " + query)

    click.echo("===================================================================")
    click.echo(f"Found {len(songs)}/{len(spotify_search_queries)}")
    click.echo(f"Flagged {len(flagged_songs)} songs\n")
    not_added_songs = []

    for flagged_song in flagged_songs:
        yt_url = f"https://youtu.be/{flagged_song['youtube_id']}"
        click.echo(
            f"Flagged '{flagged_song['name']} - {flagged_song['artists'][0]['name']}'     -----    {flagged_song['query']}  ----   {yt_url}")
        if click.confirm("Would you like to review more options for this song?", default=True):
            searched_songs = flagged_song['other_results']
            for index, searched_song in enumerate(searched_songs):
                if index == 0:
                    click.echo(f"[0] Skip/Keep song")
                else:
                    click.echo(
                        f"[{index}] {searched_song['name']} - {searched_song['artists'][0]['name']} - {searched_song['album']['name']}")

            click.echo(f"[{len(searched_songs)}] Queue song for deletion if no results match")
            option = click.prompt("Input option number", type=int, default=0)

            if option == len(searched_songs):
                not_added_songs.append(flagged_song)
            else:
                i = songs.index(flagged_song)
                chosen_song = searched_songs[option]
                chosen_song['query'] = flagged_song['query']
                chosen_song['youtube_id'] = flagged_song['youtube_id']
                songs = songs[:i] + [chosen_song] + songs[i + 1:]
            click.echo("\n")

    click.echo("\n")
    for not_added_song in not_added_songs:
        click.echo(
            f"Removed: {not_added_song['name']} - {not_added_song['artists'][0]['name']} - https://youtu.be/{not_added_song['youtube_id']}")
        if click.confirm("Would you like to search for more results for this song?", default=True):
            query = click.prompt(
                "Input your manuel search query here (Try either a simpler query or a different version)", type=str)
            searched_songs = sp.search(query, type="track", limit=9)['tracks']['items']

            for index, searched_song in enumerate(searched_songs):
                click.echo(
                    f"[{index}] {searched_song['name']} - {searched_song['artists'][0]['name']} - {searched_song['album']['name']}")

            click.echo(f"[{len(searched_songs)}] Delete song and log")
            option = click.prompt("Input option number", type=int, default=0)

            if option == len(searched_songs):
                songs.remove(not_added_song)
            else:
                i = songs.index(not_added_song)
                chosen_song = searched_songs[option]
                chosen_song['query'] = not_added_song['query']
                chosen_song['youtube_id'] = not_added_song['youtube_id']
                songs = songs[:i] + [chosen_song] + songs[i + 1:]
                not_added_songs.remove(not_added_song)
            click.echo("\n")
        else:
            songs.remove(not_added_song)
    click.echo("\n")
    for not_found_song in not_found_songs:
        click.echo(
            f"Did not find: {not_found_song['query']} - https://youtu.be/{urllib.parse.quote(not_found_song['youtube_id'])}")
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
                chosen_song['youtube_id'] = not_found_song['youtube_id']
                songs.append(chosen_song)
                not_found_songs.remove(not_found_song)
            click.echo("\n")

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
                    chosen_song['youtube_id'] = song['youtube_id']
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
    yt_playlist = get_youtube_playlist(secret_file, playlist_id)
    user_id = sp.me()['id']
    sp_playlist = sp.user_playlist_create(user_id, yt_playlist['snippet']['title'], False, False,
                                          yt_playlist['snippet']['description'])
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
            f"Permanently Removed: {not_added_song['name']} - {not_added_song['artists'][0]['name']} | {not_added_song['query']} | https://youtu.be/{urllib.parse.quote(not_added_song['youtube_id'])}")

    click.echo("\n")
    for not_found_song in not_found_songs:
        click.echo(
            f"Did not find: {not_found_song['query']} | https://youtu.be/{urllib.parse.quote(not_found_song['youtube_id'])}")
