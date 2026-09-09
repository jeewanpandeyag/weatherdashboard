# FieldClimate — Davis Weather Dashboard

An agricultural weather dashboard for Davis, California, combining:

- **Current conditions:** CIMIS Station 6 — Davis hourly temperature, wind speed and wind direction
- **Observed history:** CIMIS Station 6 daily temperature and rainfall
- **Forecast:** NOAA / National Weather Service seven-day forecast
- **Agricultural indicators:** rainfall, temperature, growing degree days (base 50°F), seasonal totals and precipitation probability

## How it works

`scripts/update_weather.py` retrieves current and historical observations from CIMIS Station 6, retrieves the NOAA forecast for Davis, and writes `data/weather.json`.

The dashboard stores the latest 370 days of CIMIS observations. Monthly rainfall is compared with a 10-year CIMIS baseline. NOAA data are used only for forecast values.

The GitHub Actions workflow runs hourly and can also be launched manually. It refreshes the dataset and deploys the static site to GitHub Pages.

## Connect CIMIS

Create a CIMIS Web API AppKey, then open **Settings → Secrets and variables → Actions → New repository secret**. Use the name `CIMIS_APP_KEY` and paste the AppKey as its value. Never put the key in this repository or share it in chat.

If the key is absent or CIMIS is temporarily unavailable, the update fails safely and the website retains the last successfully published dataset.

## Enable GitHub Pages

Open **Settings → Pages → Build and deployment**, then select **GitHub Actions** as the source. Run **Actions → Update weather dashboard → Run workflow** once to populate and publish the site.

## Data notes

- All observed temperature, rainfall, wind and growing degree day values come from CIMIS Station 6.
- Today's minimum and maximum are the range observed so far; the completed daily record becomes available later.
- Observations and forecasts are stored separately and labeled by source.
- NOAA precipitation values are forecast probabilities, not projected rainfall depth.
- Review source availability and quality flags before using the dashboard for operational decisions.

## Sources

- [California Irrigation Management Information System (CIMIS)](https://www.cimis.water.ca.gov/)
- [NOAA/NWS API documentation](https://www.weather.gov/documentation/services-web-api)

## License

Dashboard code is released under the MIT License. Weather data remain subject to their source terms and attribution.

## Live website

[Open the Davis Weather Dashboard](https://jeewanpandeyag.github.io/weatherdashboard/)
