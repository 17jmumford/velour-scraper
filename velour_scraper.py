from datetime import datetime
import json
import boto3
from bs4 import BeautifulSoup
import requests

def get_date_array() -> list[str]:
    """Get the next three months in the format YYYYMMDD."""
    current_date = datetime.now()
    next_three_months = []
    for i in range(5):
        next_month = current_date.month + i
        next_year = current_date.year
        if next_month > 12:
            next_month -= 12
            next_year += 1
        next_three_months.append(f"{next_year}{next_month:02d}01")
    return next_three_months

def get_velour_events(full_url: str) -> list[str]:  
  """Scrape the Velour website for events and dates."""
  # Headers to mimic a request from a web browser
  headers = {
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
    # Process each event
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
            # Combine the date with the event name
            # TODO: refine this
            full_event = f"{date}: {title}"
            print("adding event: ", full_event)
            event_list.append(full_event)
    return event_list

# this runs on cron job
def lambda_handler(event, context):
    """"Scrape the Velour website for events and store them in S3."""
    date_array = get_date_array()
    base_url = "https://www.velourlive.com/calendar/month.php?date="
    event_list = []
    for date in date_array:
        website_url = f"{base_url}?date={date}"
        event_list += get_velour_events(website_url)
    if len(event_list) > 0:
        # Store the results in S3
        s3 = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'velour-scraper'
        object_key = 'events.json'
        s3.put_object(Body=json.dumps(event_list), Bucket=bucket_name, Key=object_key)

        return {
            'statusCode': 200,
            'body': 'Scraping and storing data in S3 successful'
        }
    else:
        return {
            'statusCode': 500,
            'body': 'Failed to scrape website'
        }
