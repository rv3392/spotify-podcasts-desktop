from operator import itemgetter
import sched

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import pymongo

def authenticate_user() -> spotipy.Spotify:
    scope = "user-library-read, user-read-playback-position, playlist-read-private, playlist-modify-private, playlist-modify-public"
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

def init_db() -> pymongo.MongoClient:
    return pymongo.MongoClient('localhost', 27017)

def get_user_or_create(client: spotipy.Spotify, db: pymongo.collection.Collection):
    user_data = db.users.find_one({"username": client.current_user()['id']})
    if not user_data:
        user_id: pymongo.collection.InsertOneResult = db.users.insert_one({
            "listened_episodes": [],
            "shows": [],
            "unlistened_episodes": [],
            "username": client.current_user()['id']
        })
        return db.users.find_one({"_id", user_id.inserted_id})

    return user_data

def get_all_user_shows(client):
    shows = []
    offset = 0
    while True:
        results = client.current_user_saved_shows(limit=20, offset=offset)
        results = results['items']
        if len(results) == 0:
            break

        shows.extend(results)
        offset += len(results)

    return shows

def get_latest_show_episode(client: spotipy.Spotify, show_id):
    episode = client.show_episodes(show_id, limit=1)["items"][0]
    # print(episode.keys())
    # print(episode["resume_point"])
    return episode

# User Shows

def post_user_shows_to_db(db, user_id, shows):
    return db.users.update_one({"_id": user_id}, {"$addToSet": {"shows": {"$each": shows}}})

def get_user_shows(client, db):
    user_data = get_user_or_create(client, db)
    if not user_data["shows"]:
        shows = get_all_user_shows(client)
        post_user_shows_to_db(db, user_data["_id"], shows)
        return shows

    return user_data["shows"]

# User Episodes

def get_user_episodes(client: spotipy.Spotify, db: pymongo.collection.Collection):
    user_data = get_user_or_create(client, db)
    return user_data["listened_episodes"] + user_data["unlistened_episodes"]

def post_user_episodes_to_db(db: pymongo.collection.Collection, username, new_episodes):
    listened_episodes = []
    unlistened_episodes = []
    for episode in new_episodes:
        if episode["resume_point"]["fully_played"]:
            listened_episodes.append(episode)
        else:
            unlistened_episodes.append(episode)

    listened_episodes.sort(key=itemgetter("release_date"))
    unlistened_episodes.sort(key=itemgetter("release_date"))

    db.users.update_one({"username": username}, {"$addToSet": {"listened_episodes": {"$each": listened_episodes}}})
    db.users.update_one({"username": username}, {"$addToSet": {"unlistened_episodes": {"$each": unlistened_episodes}}})

def post_user_episodes_to_playlist(client: spotipy.Spotify, username, new_episodes):
    playlist = client.user_playlist_create(username, "New Podcasts", public=False)
    new_episode_ids = [episode["uri"] for episode in new_episodes]
    print(new_episode_ids)
    if new_episode_ids:
        add_items_result = client.playlist_add_items(playlist["id"], new_episode_ids)
        print(add_items_result)

def poll_new_episodes(client, db):
    new_episodes = []

    episodes = get_user_episodes(client, db)
    shows = get_user_shows(client, db)

    for show in shows:
        new_episode = get_latest_show_episode(client, show['show']['id'])
        print(new_episode["id"])
        if new_episode not in episodes:
            new_episodes.append(new_episode)

    return new_episodes

def main():
    client = authenticate_user()
    shows = get_all_user_shows(client)
    get_latest_show_episode(client, shows[0]['show']['id'])

    spotify_user =  client.current_user()['id']

    db = init_db().data
    new_episodes = poll_new_episodes(client, db)
    post_user_episodes_to_db(db, spotify_user, new_episodes)
    post_user_episodes_to_playlist(client, spotify_user, get_user_episodes(client, db))

    # for idx, item in enumerate(shows):
    #     print(idx, item['show']['name'])

if __name__ == "__main__":
    main()
