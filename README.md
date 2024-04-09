# Velour Scraper
This is a simple scraper that runs on a cron job. It scrapes velourlive.com.

## Run locally

```bash
sam build
```

```bash
sam local invoke velour-scraper
```

## TODO
0. Determine how env var/secrets are handled
1. add in AI classifier
2. add in spotify API
3. determine data format
4. deploy