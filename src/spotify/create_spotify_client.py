import spotipy
from spotipy.oauth2 import SpotifyOAuth


def create_spotify_client(client_id, client_secret):
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-library-read playlist-modify-private",
                                                     client_id=client_id,
                                                     client_secret=client_secret,
                                                     redirect_uri='http://localhost'))
