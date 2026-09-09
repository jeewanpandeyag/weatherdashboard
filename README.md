# FieldClimate — Davis Weather Dashboard

An original agricultural weather dashboard combining:

- **Current conditions:** CIMIS Station 6 — Davis (hourly temperature, wind speed and direction)\n- **Observed history:** CIMIS Station 6 — Davis daily temperature and rainfall
- **Forecast:** NOAA / National Weather Service API
- **Agricultural indicators:** rainfall, temperature, growing degree days (base 50°F), seasonal totals and precipitation probability

## How it works

`scripts/update_weather.py` requests CIMIS Station 6 hourly conditions and daily history, requests the NOAA seven-day forecast for Davis, and writes `data/weather.json`.

The GitHub Actions workflow runs hourly and can also be launched manually. It refreshes the dataset and deploys this static site to GitHub Pages.

## Connect CIMIS\n\nCreate a CIMIS Web API AppKey, then open **Settings → Secrets and variables → Actions → New repository secret**. Use the name `CIMIS_APP_KEY` and paste the AppKey as its value. Never put the key in this repository or share it in chat.\n\nIf the secret is absent or CIMIS is temporarily unavailable, the dashboard falls back to the latest UC Davis archived temperature and labels wind as pending.\n\n## Enable GitHub Pages

Open **Settings → Pages → Build and deployment**, then select **GitHub Actions** as the source. Run **Actions → Update weather dashboard → Run workflow** once to populate and publish the site.

## Data notes

- Observations and forecasts are stored separately and labeled by source.
- All observed temperature, rainfall, wind and growing degree day values come from CIMIS Station 6.
- NOAA precipitation values shown by the dashboard are forecast probabilities, not projected rainfall depth.
- Review source availability and quality flags before using the dashboard for operational decisions.

## Sources

- [NOAA/NWS API documentation](https://www.weather.gov/documentation/services-web-api)

## License

Dashboard code is released under the MIT License. Weather data remain subject to their source terms and attribution.

## Live website

[Open the Davis Weather Dashboard](https://jeewanpandeyag.github.io/weatherdashboard/)
