import os
import time
from flask import Flask, request, redirect, session, url_for, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'spotify-transfer-session'

# We need scope for reading from the old account and writing to the new one
SCOPE = 'user-library-read user-library-modify'

def create_spotify_oauth(auth_type):
    """Creates a SpotifyOAuth object with a specific cache file based on the auth_type (source or dest)"""
    cache_path = f".cache-{auth_type}"
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:5000/callback"),
        scope=SCOPE,
        cache_path=cache_path,
        show_dialog=True  # Force login screen to allow switching accounts
    )

@app.route('/')
def index():
    source_ready = os.path.exists('.cache-source')
    dest_ready = os.path.exists('.cache-dest')
    return render_template('index.html', source_ready=source_ready, dest_ready=dest_ready)

@app.route('/login/<auth_type>')
def login(auth_type):
    if auth_type not in ['source', 'dest']:
        return "Invalid auth type", 400
    session['auth_type'] = auth_type
    sp_oauth = create_spotify_oauth(auth_type)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    auth_type = session.get('auth_type')
    if not auth_type:
        return redirect(url_for('index'))
    
    sp_oauth = create_spotify_oauth(auth_type)
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    
    return redirect(url_for('index'))

@app.route('/transfer', methods=['POST'])
def transfer():
    if not os.path.exists('.cache-source') or not os.path.exists('.cache-dest'):
        return jsonify({"error": "Both accounts must be authenticated"}), 400
    
    source_oauth = create_spotify_oauth('source')
    dest_oauth = create_spotify_oauth('dest')
    
    source_token_info = source_oauth.get_cached_token()
    dest_token_info = dest_oauth.get_cached_token()
    
    if not source_token_info or not dest_token_info:
        return jsonify({"error": "Token expired or not found. Please login again."}), 401
        
    sp_source = spotipy.Spotify(auth=source_token_info['access_token'])
    sp_dest = spotipy.Spotify(auth=dest_token_info['access_token'])
    
    # Fetch all liked songs from source
    liked_songs = []
    try:
        results = sp_source.current_user_saved_tracks(limit=50)
        while results:
            for item in results['items']:
                liked_songs.append(item['track']['id'])
            if results['next']:
                results = sp_source.next(results)
            else:
                break
    except Exception as e:
        return jsonify({"error": f"Failed to fetch songs from old account: {str(e)}"}), 500
            
    # Add to destination in batches of 50 (Spotify API limit)
    try:
        for i in range(0, len(liked_songs), 50):
            batch = liked_songs[i:i+50]
            sp_dest.current_user_saved_tracks_add(tracks=batch)
    except Exception as e:
        return jsonify({"error": f"Failed to add songs to new account: {str(e)}"}), 500
        
    return jsonify({"success": True, "transferred": len(liked_songs)})

@app.route('/logout')
def logout():
    if os.path.exists('.cache-source'):
        os.remove('.cache-source')
    if os.path.exists('.cache-dest'):
        os.remove('.cache-dest')
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting Spotify Transfer Tool...")
    print("Go to http://localhost:5000 in your web browser!")
    app.run(debug=True, port=5000)
