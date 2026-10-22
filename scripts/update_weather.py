#!/usr/bin/env python3
import io, json, os, re, time, urllib.error, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,"data","weather.json")
LAT,LON=38.5353,-121.7733
PACIFIC=ZoneInfo("America/Los_Angeles")
UA={"User-Agent":"Davis AgWeather dashboard (github.com/jeewanpandeyag/weatherdashboard)"}
CIMIS_URL="https://et.water.ca.gov/StationWeb/GetDataByStationNumber"
LIVE_STATION_URL="https://api.weather.gov/stations/KEDU/observations/latest"
UCD_RAIN_URL="https://apps.atm.ucdavis.edu/wxdata/data/CT_Rain_mm.zip"
RAIN_REPORT_STATION="KSAC"

def fetch(url,headers=None,attempts=4):
    """Fetch an API response, tolerating brief CIMIS/NOAA interruptions."""
    req=urllib.request.Request(url,headers={**UA,**(headers or {})})
    for attempt in range(1,attempts+1):
        try:
            with urllib.request.urlopen(req,timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            # Retrying a bad request or authentication failure only delays a
            # useful error. Rate limits and server failures are often brief.
            retryable=error.code in (408,425,429) or error.code>=500
            if not retryable or attempt==attempts:
                raise RuntimeError(
                    f"Weather API request failed with HTTP {error.code} "
                    f"after {attempt} attempt(s): {url}"
                ) from error
        except (urllib.error.URLError,TimeoutError) as error:
            if attempt==attempts:
                raise RuntimeError(
                    f"Weather API request failed after {attempt} attempts: "
                    f"{url} ({error})"
                ) from error
        delay=2**(attempt-1)
        print(f"Weather API temporarily unavailable; retrying in {delay}s "
              f"(attempt {attempt+1}/{attempts})")
        time.sleep(delay)

def field_value(record,name):
    try:
        return float(record.get(name,{}).get("Value"))
    except (TypeError,ValueError):
        return None

def cimis_records(start,end,is_hourly,items):
    key=os.getenv("CIMIS_APP_KEY")
    if not key:
        raise RuntimeError("CIMIS_APP_KEY is required")
    params=urlencode({
        "stationNbrs":"6",
        "startDate":start.isoformat(),
        "endDate":end.isoformat(),
        "isHourly":"true" if is_hourly else "false",
        "dataItems":",".join(items),
        "unitOfMeasure":"E"
    })
    headers={"Accept":"application/json","Ocp-Apim-Subscription-Key":key}
    data=json.loads(fetch(CIMIS_URL+"?"+params,headers))
    records=[]
    for provider in data.get("Data",{}).get("Providers",[]):
        records.extend(provider.get("Records",[]))
    return records

def cimis_daily_records_chunked(start,end,items,chunk_days=180):
    """Keep daily requests below CIMIS's date-range limit."""
    records=[]
    chunk_start=start
    while chunk_start<=end:
        chunk_end=min(chunk_start+timedelta(days=chunk_days-1),end)
        records.extend(cimis_records(chunk_start,chunk_end,False,items))
        chunk_start=chunk_end+timedelta(days=1)
    return records

def compass(degrees):
    names=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return names[round(degrees/22.5)%16]

def noaa_current_observation():
    properties=json.loads(fetch(LIVE_STATION_URL))["properties"]
    temperature_c=properties.get("temperature",{}).get("value")
    wind_kmh=properties.get("windSpeed",{}).get("value")
    direction=properties.get("windDirection",{}).get("value")
    timestamp=properties.get("timestamp")
    if temperature_c is None or not timestamp:
        raise RuntimeError("NOAA KEDU returned no current temperature")
    observed=datetime.fromisoformat(timestamp.replace("Z","+00:00")).astimezone(PACIFIC)
    return {
        "temperatureF":round(temperature_c*9/5+32,1),
        "date":observed.date().isoformat(),
        "recordedAt":observed.strftime("%Y-%m-%d %H:%M"),
        "windMph":round(wind_kmh/1.609344,1) if wind_kmh is not None else None,
        "windDirectionDeg":round(direction) if direction is not None else None,
        "windDirection":compass(direction) if direction is not None else None,
        "source":"NOAA KEDU — University Airport",
        "distanceMi":0.9
    }

def cimis_current(today):
    records=cimis_records(today-timedelta(days=1),today,True,[
        "hly-air-tmp","hly-wind-spd","hly-wind-dir","hly-precip"
    ])
    records=[r for r in records if r.get("Scope")=="hourly" and field_value(r,"HlyAirTmp") is not None]
    if not records:
        raise RuntimeError("CIMIS returned no hourly observations for Station 6")
    latest=max(records,key=lambda r:(r.get("Date",""),r.get("Hour","")))
    temp=field_value(latest,"HlyAirTmp")
    speed=field_value(latest,"HlyWindSpd")
    direction=field_value(latest,"HlyWindDir")
    hour=latest.get("Hour","")
    today_records=[r for r in records if r.get("Date")==today.isoformat()]
    today_temps=[field_value(r,"HlyAirTmp") for r in today_records]
    today_temps=[v for v in today_temps if v is not None]
    today_rain=sum(max(field_value(r,"HlyPrecip") or 0,0) for r in today_records)
    clock=(hour[:2]+":"+hour[2:]) if len(hour)==4 else hour
    return {
        "temperatureF":round(temp,1),
        "date":latest["Date"],
        "recordedAt":latest["Date"]+" "+clock,
        "todayHighF":round(max(today_temps),1) if today_temps else None,
        "todayLowF":round(min(today_temps),1) if today_temps else None,
        "todayRainIn":round(today_rain,3),
        "windMph":round(speed,1) if speed is not None else None,
        "windDirectionDeg":round(direction) if direction is not None else None,
        "windDirection":compass(direction) if direction is not None else None,
        "source":"CIMIS Station 6 — Davis"
    }

def ucd_recent_rain(start,end):
    """Aggregate the UC Davis Campbell Tract five-minute rain gauge."""
    totals=defaultdict(float)
    archive_bytes=fetch(UCD_RAIN_URL)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        csv_name=archive.namelist()[0]
        with archive.open(csv_name) as rows:
            for raw in rows:
                try:
                    _,_,value,timestamp=raw.decode("utf-8").strip().split(",",3)
                    day=datetime.fromisoformat(timestamp).date()
                    if day>end:
                        continue
                    if day<start:
                        break
                    totals[day.isoformat()]+=max(float(value),0)/25.4
                except (UnicodeDecodeError,ValueError):
                    continue
    return {day:round(value,3) for day,value in totals.items()}

def noaa_recent_rain_reports(start,end):
    """Capture light/trace rain reports that a tipping gauge can miss."""
    start_utc=datetime.combine(start,datetime.min.time(),PACIFIC).astimezone(timezone.utc)
    end_utc=datetime.combine(end+timedelta(days=1),datetime.min.time(),PACIFIC).astimezone(timezone.utc)
    query=urlencode({
        "start":start_utc.isoformat().replace("+00:00","Z"),
        "end":end_utc.isoformat().replace("+00:00","Z"),
        "limit":"500"
    })
    url=f"https://api.weather.gov/stations/{RAIN_REPORT_STATION}/observations?{query}"
    features=json.loads(fetch(url)).get("features",[])
    days=defaultdict(lambda:{"observed":False,"hourly":{}})
    for feature in features:
        properties=feature.get("properties",{})
        timestamp=properties.get("timestamp")
        if not timestamp:
            continue
        observed=datetime.fromisoformat(timestamp.replace("Z","+00:00")).astimezone(PACIFIC)
        day=observed.date()
        if day<start or day>end:
            continue
        raw=properties.get("rawMessage") or ""
        present=properties.get("presentWeather") or []
        rain_code=bool(re.search(r"(?:^|\s)[+-]?(?:SH)?RA(?:\s|$)",raw))
        rain_code=rain_code or any("rain" in str(item).lower() for item in present)
        amount=properties.get("precipitationLastHour",{}).get("value")
        if amount is not None:
            amount=max(float(amount),0)
            key=observed.strftime("%Y-%m-%d %H")
            days[day.isoformat()]["hourly"][key]=max(days[day.isoformat()]["hourly"].get(key,0),amount)
        days[day.isoformat()]["observed"]|=rain_code or (amount is not None and amount>0)
    return {
        day:{"observed":values["observed"],"nearbyIn":round(sum(values["hourly"].values())/25.4,3)}
        for day,values in days.items()
    }

def cimis_daily_history(today,days=370):
    records=cimis_daily_records_chunked(today-timedelta(days=days-1),today,[
        "day-air-tmp-max","day-air-tmp-min","day-precip"
    ])
    rows=[]
    for record in records:
        high=field_value(record,"DayAirTmpMax")
        low=field_value(record,"DayAirTmpMin")
        if high is None or low is None:
            continue
        day=record.get("Date")
        rain=max(field_value(record,"DayPrecip") or 0,0)
        rows.append({
            "date":day,
            "label":datetime.fromisoformat(day).strftime("%b %-d"),
            "high":round(high,1),
            "low":round(low,1),
            "rain":round(rain,3),
            "gdd":round(max(0,(high+low)/2-50),1),
            "source":"CIMIS Station 6 — Davis"
        })
    return sorted(rows,key=lambda row:row["date"])

def noaa_forecast():
    point=json.loads(fetch(f"https://api.weather.gov/points/{LAT},{LON}"))
    periods=json.loads(fetch(point["properties"]["forecast"]))["properties"]["periods"]
    by={}
    for period in periods:
        day=period["startTime"][:10]
        row=by.setdefault(day,{
            "date":day,"label":datetime.fromisoformat(day).strftime("%b %-d"),
            "high":None,"low":None,"rain":0,"pop":0,"summary":[],
            "windMph":0,"windDirection":[],"hasDayForecast":False,"hasNightForecast":False,"source":"NOAA / NWS"
        })
        temp=period["temperature"] if period["temperatureUnit"]=="F" else period["temperature"]*9/5+32
        row["high" if period["isDaytime"] else "low"]=round(temp,1)
        row["hasDayForecast" if period["isDaytime"] else "hasNightForecast"]=True
        row["pop"]=max(row["pop"],period.get("probabilityOfPrecipitation",{}).get("value") or 0)
        row["summary"].append(period["shortForecast"])
        speeds=[int(v) for v in re.findall(r"\d+",period.get("windSpeed",""))]
        row["windMph"]=max(row["windMph"],max(speeds) if speeds else 0)
        row["windDirection"].append(period.get("windDirection",""))
    rows=[]
    for row in by.values():
        # NOAA's final forecast day may include only a daytime or nighttime
        # period. Keep the missing value null instead of inventing a daily
        # range by copying the one period into both high and low.
        row["gdd"]=(
            round(max(0,(row["high"]+row["low"])/2-50),1)
            if row["high"] is not None and row["low"] is not None
            else None
        )
        row["summary"]=" / ".join(row["summary"])
        row["windDirection"]=" / ".join(dict.fromkeys(v for v in row["windDirection"] if v))
        rows.append(row)
    return rows[:7]

def cached_cimis_normals():
    try:
        with open(OUT) as source:
            monthly=json.load(source).get("monthly",[])
        if len(monthly)==12 and all(row.get("historicalSource")=="CIMIS Station 6 — Davis" for row in monthly):
            return {index+1:row.get("historical") for index,row in enumerate(monthly)}
    except (OSError,ValueError,TypeError):
        pass
    return None

def cimis_monthly_normals(first_year,last_year):
    totals=defaultdict(float)
    for year in range(first_year,last_year+1):
        records=cimis_records(datetime(year,1,1).date(),datetime(year,12,31).date(),False,["day-precip"])
        for record in records:
            rain=field_value(record,"DayPrecip")
            if rain is not None:
                day=datetime.fromisoformat(record["Date"]).date()
                totals[(day.year,day.month)]+=max(rain,0)
    years=last_year-first_year+1
    return {month:round(sum(totals[(year,month)] for year in range(first_year,last_year+1))/years,2) for month in range(1,13)}

def monthly_comparison(history,today,normals):
    totals=defaultdict(float)
    for row in history:
        day=datetime.fromisoformat(row["date"]).date()
        if day.year==today.year:
            totals[day.month]+=row["rain"]
    return [{
        "month":datetime(2000,month,1).strftime("%b"),
        "current":round(totals[month],2) if month<=today.month else None,
        "historical":normals.get(month),
        "years":10,
        "historicalSource":"CIMIS Station 6 — Davis"
    } for month in range(1,13)]

def main():
    today=datetime.now(PACIFIC).date()
    current=cimis_current(today)
    live=noaa_current_observation()
    history=cimis_daily_history(today)
    recent_rain=ucd_recent_rain(today-timedelta(days=14),today)
    try:
        rain_reports=noaa_recent_rain_reports(today-timedelta(days=14),today)
    except RuntimeError as error:
        print(f"NOAA rain occurrence feed unavailable: {error}")
        rain_reports={}
    for row in history:
        if row["date"] in recent_rain:
            row["rain"]=recent_rain[row["date"]]
            row["rainSource"]="UC Davis Campbell Tract"
        report=rain_reports.get(row["date"])
        if report and report["observed"] and row["rain"]<.001:
            row["rainObserved"]=True
            row["rainNote"]="Trace/light rain observed nearby"
            row["rainReportSource"]="NOAA KSAC — Sacramento Executive Airport"
    if today.isoformat() in recent_rain:
        current["todayRainIn"]=recent_rain[today.isoformat()]
        current["rainSource"]="UC Davis Campbell Tract"
    if current.get("date")==today.isoformat() and current.get("todayHighF") is not None:
        today_row={
            "date":today.isoformat(),
            "label":today.strftime("%b %-d"),
            "high":current["todayHighF"],
            "low":current["todayLowF"],
            "rain":current["todayRainIn"],
            "gdd":round(max(0,(current["todayHighF"]+current["todayLowF"])/2-50),1),
            "source":"CIMIS Station 6 — Davis (today so far)"
        }
        history=[row for row in history if row["date"]!=today.isoformat()]+[today_row]
        history.sort(key=lambda row:row["date"])
    normals=cached_cimis_normals() or cimis_monthly_normals(today.year-10,today.year-1)
    data={
        "location":{"name":"Davis, California","latitude":LAT,"longitude":LON},
        "updatedAt":datetime.now(timezone.utc).isoformat(),
        "live":live,
        "current":current,
        "history":history,
        "forecast":noaa_forecast(),
        "monthly":monthly_comparison(history,today,normals),
        "sources":{
            "live":"NOAA KEDU — University Airport",
            "observed":"CIMIS Station 6 — Davis",
            "rain":"UC Davis Campbell Tract",
            "rainOccurrence":"NOAA KSAC — Sacramento Executive Airport",
            "forecast":"NOAA / National Weather Service API"
        }
    }
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,"w") as output:
        json.dump(data,output,separators=(",",":"))

if __name__=="__main__":
    main()
