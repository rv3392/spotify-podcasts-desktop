import sched

import spotipy

from spotipy.oauth2 import SpotifyOAuth

def authenticate_user():
    scope = "user-library-read"
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

def get_all_user_shows(client):
    shows = []
    offset = 0
    while True:
        results = client.current_user_saved_shows(limit=50, offset=offset)
        results = results['items']
        if len(results) == 0:
            break

        shows.extend(results)
        offset += len(results)

    return shows

def get_latest_show_episode(client, show_id):
    episodes = client.show_episodes(show_id, limit=5)
    for episode in episodes['items']:
        print(episode['release_date'])

def poll_new_episodes():
    pass

def main():
    client = authenticate_user()
    shows = get_all_user_shows(client)
    get_latest_show_episode(client, shows[0]['show']['id'])

    # for idx, item in enumerate(shows):
    #     print(idx, item['show']['name'])

if __name__ == "__main__":
    main()
