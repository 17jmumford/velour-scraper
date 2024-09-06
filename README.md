# Velour Scraper
This is a simple scraper that runs on a cron job. It scrapes velourlive.com.

## Run locally

```bash
pip install -r requirements.txt
pip install -r requirements.txt -t package
```

```bash
sam build
```

```bash
sam local invoke velour-scraper
```

## TODO
0. Determine how env var/secrets are handled DONE
1. add in AI classifier DONE
2. add in spotify API
3. determine data format
4. deploy