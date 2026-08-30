# Spotify Liked Songs Transfer Tool

A simple local Python web application that allows you to easily transfer your "Liked Songs" from one Spotify account to another with just a few clicks.

## How to Set It Up

Spotify requires apps to be registered in order to use their API. Follow these steps to get your API keys:

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in with your primary Spotify account.
2. Click **"Create app"**.
3. Fill in the App name (e.g., "My Transfer Tool") and App description.
4. For **Redirect URI**, you **MUST** enter exactly: `http://localhost:5000/callback`
5. Check the Developer Terms of Service and click **"Save"**.
6. Once created, click on **"Settings"** in your new app.
7. You will see your **Client ID** and **Client Secret** (you may need to click "View client secret").
8. Copy the `.env.example` file to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
9. Open the `.env` file and paste your `Client ID` and `Client Secret` into the appropriate fields.

## How to Run the App

1. Install the required Python packages (it's recommended to use a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app.py
   ```
3. Open your web browser and go to `http://localhost:5000`.
4. Follow the on-screen prompts:
   - Click **Login to Old Account** and authorize.
   - Click **Login to New Account** and authorize. 
   - Click **Transfer Liked Songs!**

> **Note:** The Spotify API allows fetching and adding tracks in batches of 50. The script automatically handles this process for you.
