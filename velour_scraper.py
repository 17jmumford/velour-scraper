"""This is the most important file in the repo."""
from datetime import datetime
import json
from typing import Any
import boto3
from bs4 import BeautifulSoup
import requests
from openai import OpenAI
import os

def next_x_months(x: int) -> list[str]:
    """Get the next x months in the format YYYYMMDD."""
    current_date = datetime.now()
    next_two_months = []
    for i in range(x):
        next_month = current_date.month + i
        next_year = current_date.year
        if next_month > 12:
            next_month -= 12
            next_year += 1
        next_two_months.append(f"{next_year}{next_month:02d}01")
    return next_two_months


def get_spotify_bearer_token() -> str:
    """Get the bearer token for the Spotify API."""
    url = "https://accounts.spotify.com/api/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials',
            'client_id': os.environ['SpotifyClientID'],
            'client_secret': os.environ['SpotifyClientSecret']}
    response = requests.post(url, headers=headers, data=data)
    print(response.json())
    return response.json()['access_token']

def fetch_spotify_data(bearer_token: str, artist_name: str) -> dict[str, Any]:
    """Fetch data from the Spotify API."""
    artist = artist_name.replace(" ", "+")
    url = f"https://api.spotify.com/v1/search?q={artist}&type=artist&market=US&limit=1"
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }
    response = requests.get(url, headers=headers)
    artist_data = response.json()['artists']['items'][0]
    top_tracks = requests.get(artist_data['href'] + '/top-tracks?market=US', headers=headers)
    top_five_tracks = top_tracks.json()['tracks'][:5]
    artist_and_top_tracks = {
        "artist": artist_data,
        "top_tracks": top_five_tracks
    }
    return artist_and_top_tracks

def clean_event(event: str) -> dict[str, str]:
    """Take a messy event string and return a cleaned response using ai."""
    client = OpenAI(api_key=os.environ['OpenAIAPIKey'])
    prompt = f"""
    You are a helpful assistant that cleans event strings from a local music venue's website.
    Here is the event string: {event}.
    An event string has everything happening on a given day at the venue.
    There may be multiple artists, or just one, or even no artists, just a note on the event.
    Return a json object with the following keys:
    {{artists: [list of artists], special_notes: extra-info}}
    --Some examples of what you should return--
    If a date is a special event, such as Open-Mic Night, return the following:
    {{artists: [], special_notes: "Open Mic Night"}}
    If a date has several artists with some extra info, such as
    (Indie/Folk) Caleb Darger "Album Release" w/ The Company,Amanda on the Moon(LA)
    return the following:
    {{artists: ["Caleb Darger", "The Company", "Amanda on the Moon"], special_notes: "Indie/Folk artists, plus album release by Caleb Darger"}}
    If there is no extra info, just provide an empty string.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt},
        ],
        response_format={ "type": "json_object" }
    )
    return json.loads(response.choices[0].message.content)


def get_velour_events(full_url: str, spotify_bearer_token: str) -> list[str]:  
  """Scrape the Velour websites for events and dates."""
  headers = { # spoof like a browser
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  }
  response = requests.get(full_url, headers=headers)

  if response.status_code == 200:
    # Parse the html content
    print(f"Scraping {full_url}")
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find all 'td' elements which potentially contain dates and events
    events = soup.find_all('td')
    event_list = []
    for event in events:
      # skip all the 'td' elements that wrap the inner ones by checking for table element
      bad_element = event.find('table', class_='main')
      if not bad_element:
        # Find the date within each 'td' element
        date_span = event.find('span', class_='dayofmonth')
        if date_span:
          date = date_span.text.strip()
          # Find all event names (performing artists) within the same 'td' element
          for entry in event.find_all('a', class_='entry'):
            title = entry.text.strip()
            cleaned_event = clean_event(title)
            spotify_data = []
            for artist in cleaned_event['artists']:
              spotify_data.append(fetch_spotify_data(spotify_bearer_token, artist))
            cleaned_event['spotify_data'] = spotify_data
            full_event = {date: cleaned_event}
            print("adding event: ", full_event)
            event_list.append(full_event)
    return event_list


# TODO: manually add cron job trigger in UI
def lambda_handler(event, context):
    """"Scrape the Velour website for events and store them in S3."""
    date_array = next_x_months(2)
    base_url = "https://www.velourlive.com/calendar/month.php?date="
    event_list = []
    spotify_bearer_token = get_spotify_bearer_token()
    for date in date_array:
        website_url = f"{base_url}?date={date}"
        event_list += {date: get_velour_events(website_url, spotify_bearer_token)}
    if len(event_list) > 0:
        s3 = boto3.client('s3', region_name='us-west-2')
        s3.put_object(Body=json.dumps(event_list), Bucket='velour-scraper', Key='events.json')
        return {
            'statusCode': 200,
            'body': 'Scraping and storing data in S3 successful'
        }
    else:
        return {'statusCode': 500, 'body': 'Failed to scrape website'}