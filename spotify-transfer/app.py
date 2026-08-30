import os
from flask import Flask, request, redirect, session, url_for, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
app.config['SESSION_COOKIE_NAME'] = 'spotify-transfer-session'

SCOPE = 'user-library-read user-library-modify'

class CustomFlaskSessionCacheHandler(CacheHandler):
    def __init__(self, session, key):
        self.session = session
        self.key = key

    def get_cached_token(self):
        return self.session.get(self.key)

    def save_token_to_cache(self, token_info):
        self.session[self.key] = token_info

def create_spotify_oauth(auth_type):
    cache_handler = CustomFlaskSessionCacheHandler(session, key=f"token_info_{auth_type}")
    
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE,
        cache_handler=cache_handler,
        show_dialog=True 
    )

@app.route('/')
def index():
    source_oauth = create_spotify_oauth('source')
    dest_oauth = create_spotify_oauth('dest')
    
    source_ready = source_oauth.validate_token(source_oauth.cache_handler.get_cached_token()) is not None
    dest_ready = dest_oauth.validate_token(dest_oauth.cache_handler.get_cached_token()) is not None
    
    return render_template('index.html', source_ready=source_ready, dest_ready=dest_ready)

@app.route('/login/<auth_type>')
def login(auth_type):
    if auth_type not in ['source', 'dest']:
        return "Invalid auth type", 400
    session['current_auth_type'] = auth_type
    sp_oauth = create_spotify_oauth(auth_type)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    auth_type = session.get('current_auth_type')
    if not auth_type:
        return redirect(url_for('index'))
    
    sp_oauth = create_spotify_oauth(auth_type)
    code = request.args.get('code')
    sp_oauth.get_access_token(code)
    
    session.pop('current_auth_type', None)
    return redirect(url_for('index'))

@app.route('/transfer', methods=['POST'])
def transfer():
    source_oauth = create_spotify_oauth('source')
    dest_oauth = create_spotify_oauth('dest')
    
    source_token_info = source_oauth.get_cached_token()
    dest_token_info = dest_oauth.get_cached_token()
    
    if not source_token_info or not dest_token_info:
        return jsonify({"error": "Both accounts must be authenticated. Please login again."}), 401
        
    sp_source = spotipy.Spotify(auth=source_token_info['access_token'])
    sp_dest = spotipy.Spotify(auth=dest_token_info['access_token'])
    
    liked_songs = []
    try:
        results = sp_source.current_user_saved_tracks(limit=50)
        while results:
            for item in results['items']:
                track = item.get('track')
                if not track:
                    continue
                
                # CRITICAL FIX: Skip local files (MP3s) and tracks that have been removed from Spotify
                # Attempting to add a local file or a removed track to a new account causes a 403 Forbidden!
                if track.get('is_local') or track.get('id') is None:
                    continue
                    
                liked_songs.append(track['id'])
                
            if results['next']:
                results = sp_source.next(results)
            else:
                break
    except Exception as e:
        return jsonify({"error": f"Failed to fetch songs from old account: {str(e)}"}), 500
            
    success_count = 0
    try:
        for i in range(0, len(liked_songs), 50):
            batch = liked_songs[i:i+50]
            try:
                # Try adding the batch of 50
                sp_dest.current_user_saved_tracks_add(tracks=batch)
                success_count += len(batch)
            except Exception as e:
                # If the batch fails (e.g. because 1 song in the 50 is regionally locked), 
                # fallback to adding them one by one so the whole batch doesn't fail
                for track_id in batch:
                    try:
                        sp_dest.current_user_saved_tracks_add(tracks=[track_id])
                        success_count += 1
                    except Exception as fallback_e:
                        print(f"Skipped problematic track {track_id}: {fallback_e}")
                        continue
                        
    except Exception as e:
        return jsonify({"error": f"Failed to add songs to new account: {str(e)}"}), 500
        
    return jsonify({"success": True, "transferred": success_count})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
