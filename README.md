# FieldClimate — UC Davis Weather Dashboard

An original agricultural weather dashboard combining:

- **Historical observations:** UC Davis Campbell Tract Weather & Climate Station archive
- **Forecast:** NOAA / National Weather Service API
- **Agricultural indicators:** rainfall, temperature, growing degree days (base 50°F), seasonal totals and precipitation probability

## How it works

`scripts/update_weather.py` downloads the public UC Davis temperature and rainfall archives, aggregates five-minute observations into daily records, requests the NOAA seven-day forecast for Davis, and writes `data/weather.json`.

The GitHub Actions workflow runs every day and can also be launched manually. It refreshes the dataset and deploys this static site to GitHub Pages.

## Enable GitHub Pages

Open **Settings → Pages → Build and deployment**, then select **GitHub Actions** as the source. Run **Actions → Update weather dashboard → Run workflow** once to populate and publish the site.

## Data notes

- Observations and forecasts are stored separately and labeled by source.
- UC Davis archive values are aggregated from five-minute records.
- NOAA precipitation values shown by the dashboard are forecast probabilities, not projected rainfall depth.
- Review source availability and quality flags before using the dashboard for operational decisions.

## Sources

- [UC Davis Weather & Climate Station](https://atm.ucdavis.edu/weather/uc-davis-weather-climate-station)
- [NOAA/NWS API documentation](https://www.weather.gov/documentation/services-web-api)

## License

Dashboard code is released under the MIT License. Weather data remain subject to their source terms and attribution.

## Live website

[Open the UC Davis Weather Dashboard](https://jeewanpandeyag.github.io/weatherdashboard/)
