import json
from flask import Flask, request, redirect, g, render_template
import requests
from urllib.parse import quote
from datetime import datetime, timedelta
from collections import Counter
from client import CLIENT_ID,CLIENT_SECRET

app = Flask(__name__)



SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)


CLIENT_SIDE_URL = "http://localhost"
PORT = 8888
REDIRECT_URI = "{}:{}/callback".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "client_id": CLIENT_ID
}

playlist_array_andre = []
playlist_array_pedro = []

def get_playlist(playlist_url, authorization_header):
    api_url = "https://api.spotify.com/v1/playlists/" + playlist_url +"/tracks"
    day = 0
    startDate = '01/01/2019'

    playlist_array = []
    artists = []
    for x in range(0,400,100):
        r =  requests.get(api_url, headers=authorization_header, params={'market' : 'PT', 'offset' : x, 'fields' : 'items(track(name,artists(name),album(name)))'})
        playlist_data = json.loads(r.text)

        for item in playlist_data["items"]:
        
            album_name = item["track"]["album"]["name"]
            song_name = item["track"]["name"]
            for artist in item["track"]["artists"]:
                artists.append(artist["name"])
            artists_names = artists.copy()    

            date = datetime.strptime(startDate, "%d/%m/%Y")
            modified_date = date + timedelta(days=day)
            date = datetime.strftime(modified_date, "%d/%m/%Y")

            day += 1

            playlist_array.append({
                "artists" : artists_names,
                "song" : song_name,
                "album" : album_name,
                "date" : date
            })
            artists.clear()
    
    return playlist_array



def playlist_into_json(playlist,user_name):
    file = open("playlist_"+user_name+".json","w")
    
    file.write('{"data":[')
    for num,item in enumerate(playlist,start=1):
        file.write(json.dumps(item))
        if num < len(playlist):
            file.write(',')
        else:
            file.write(']')
        
    file.write('}')
    file.close()


def top_artists(playlist,number):
    top = []
    for item in playlist["data"]:
        for artist in item["artists"]:
            top.append(artist)
    res = Counter(top).most_common(number)
    return res

def top_albums(playlist,number):
    top = []
    for item in playlist["data"]:
        top.append(item["album"])
    res = Counter(top).most_common(number)
    return res   

def equal_artists(playlist1,playlist2):
    artists1 = set()
    artists2 = set()
    for item in playlist1["data"]:
        for artist in item["artists"]:
            artists1.add(artist)

    for item in playlist2["data"]:
        for artist in item["artists"]:
            artists2.add(artist)
    
    res = artists1 & artists2
    return (res,len(res))

def equal_albums(playlist1,playlist2):
    albums1 = set()
    albums2 = set()
    for a,b in zip(playlist1["data"],playlist2["data"]):
        albums1.add(a["album"])
        albums2.add(b["album"])

    res = albums1 & albums2
    return (res,len(res))

def equal_songs(playlist1,playlist2):
    musics1 = set()
    musics2 = set()
    for a,b in zip(playlist1["data"],playlist2["data"]):
        musics1.add(a["song"])
        musics2.add(b["song"])
    
    res = musics1 & musics2
    return (res,len(res))

def same_day_songs(playlist1,playlist2):
    res = []
    for a,b in zip(playlist1["data"],playlist2["data"]):
        if a["song"] == b["song"] and a["album"] == b["album"]:
            res.append(a)
    
    return res

@app.route("/")
def index():
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)

@app.route("/stats")
def stats():
    with open('playlist_andre.json','r') as jsonfile1:
        playlist1 = json.load(jsonfile1)
    
    with open('playlist_pedro.json','r') as jsonfile2:
        playlist2 = json.load(jsonfile2)
 
    samesongs = equal_songs(playlist1,playlist2)
    sameartists = equal_artists(playlist1,playlist2)
    samealbums = equal_albums(playlist1,playlist2)

    return render_template("stats.html", same_songs=samesongs[0], same_artists =sameartists[0], 
                    same_albums = samealbums[0], nr_equal_songs=samesongs[1], nr_equal_artists=sameartists[1],
                    nr_equal_albums=samealbums[1],same_day=same_day_songs(playlist1,playlist2))

@app.route("/tops")
def tops():
    with open('playlist_andre.json','r') as jsonfile1:
        playlist1 = json.load(jsonfile1)
    
    with open('playlist_pedro.json','r') as jsonfile2:
        playlist2 = json.load(jsonfile2)
    
    top_artistas_andre = top_artists(playlist1,5)
    top_artistas_pedro = top_artists(playlist2,5)

    top_albuns_andre = top_albums(playlist1,5)
    top_albuns_pedro = top_albums(playlist2,5)

    return render_template("tops.html", top_artistas=list(zip(top_artistas_andre,top_artistas_pedro)), 
                            top_albuns = list(zip(top_albuns_andre,top_albuns_pedro)))

@app.route("/playlists")
def playlists():
    with open('playlist_andre.json','r') as jsonfile1:
        playlist1 = json.load(jsonfile1)
    
    with open('playlist_pedro.json','r') as jsonfile2:
        playlist2 = json.load(jsonfile2)
    
    print(top_artists(playlist1,10))
    print(same_day_songs(playlist1,playlist2))

    return render_template("playlists.html", playlist=list(zip(playlist1["data"],playlist2["data"])), 
                            nr_andre = len(playlist1["data"]), nr_pedro = len(playlist2["data"]), 
                            sorted_array_andre=playlist1["data"], sorted_array_pedro=playlist2["data"])


@app.route("/callback")
def callback():
    
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)

    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    
    # Get user playlist data
    playlist_array_pedro = get_playlist("71GKbzOM6zfQzujELbJ8oD",authorization_header)
    playlist_array_andre = get_playlist("7u0yuqLL5ZzvG1KRl2bucq",authorization_header)

    

    playlist_into_json(playlist_array_andre,'andre')
    playlist_into_json(playlist_array_pedro,'pedro')
    
    return stats()
    

if __name__ == "__main__":
    app.run(debug=True, port=PORT)

