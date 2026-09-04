#!/usr/bin/env python3
import csv, io, json, os, tempfile, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=os.path.join(ROOT,"data","weather.json")
UCD="https://apps.atm.ucdavis.edu/wxdata/data/"; LAT,LON=38.5353,-121.7733
UA={"User-Agent":"FieldClimate weatherdashboard (github.com/jeewanpandeyag/weatherdashboard)"}
def fetch(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def recent_sensor(name,days=370):
    raw=fetch(UCD+name+".zip"); cutoff=(datetime.now()-timedelta(days=days)).date() if days else None; out=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z, z.open(z.namelist()[0]) as f:
        for row in csv.reader(io.TextIOWrapper(f)):
            if len(row)<4:continue
            try:dt=datetime.strptime(row[3],"%Y-%m-%d %H:%M:%S");val=float(row[2])
            except ValueError:continue
            if cutoff and dt.date()<cutoff:break
            out.append((dt,val))
    return out
def daily_history(rain_all):
    temps=recent_sensor("CT_Ta2m"); cutoff=(datetime.now()-timedelta(days=370)).date(); rain=[(d,v) for d,v in rain_all if d.date()>=cutoff]; by=defaultdict(lambda:{"temps":[],"rainmm":0})
    for d,v in temps:by[d.date().isoformat()]["temps"].append(v)
    for d,v in rain:by[d.date().isoformat()]["rainmm"]+=max(v,0)
    rows=[]
    for day in sorted(by):
        vals=by[day]["temps"]
        if not vals:continue
        hi=max(vals)*9/5+32;lo=min(vals)*9/5+32;gdd=max(0,(hi+lo)/2-50)
        rows.append({"date":day,"label":datetime.fromisoformat(day).strftime("%b %-d"),"high":round(hi,1),"low":round(lo,1),"rain":round(by[day]["rainmm"]/25.4,3),"gdd":round(gdd,1),"source":"UC Davis Campbell Tract"})
    return rows
def noaa_forecast():
    point=json.loads(fetch(f"https://api.weather.gov/points/{LAT},{LON}"));url=point["properties"]["forecast"]
    periods=json.loads(fetch(url))["properties"]["periods"];by={}
    for p in periods:
        day=p["startTime"][:10];r=by.setdefault(day,{"date":day,"label":datetime.fromisoformat(day).strftime("%b %-d"),"high":None,"low":None,"rain":0,"pop":0,"summary":[],"source":"NOAA / NWS"})
        temp=p["temperature"] if p["temperatureUnit"]=="F" else p["temperature"]*9/5+32
        r["high" if p["isDaytime"] else "low"]=round(temp,1);r["pop"]=max(r["pop"],p.get("probabilityOfPrecipitation",{}).get("value") or 0);r["summary"].append(p["shortForecast"])
    rows=[]
    for r in by.values():
        if r["high"] is None:r["high"]=r["low"]
        if r["low"] is None:r["low"]=r["high"]
        r["gdd"]=round(max(0,(r["high"]+r["low"])/2-50),1);r["summary"]=" / ".join(r["summary"]);rows.append(r)
    return rows[:7]
def monthly_comparison(rain_records):
    totals=defaultdict(float)
    for d,v in rain_records:totals[(d.year,d.month)]+=max(v,0)/25.4
    current_year=datetime.now().year; rows=[]
    for month in range(1,13):
        historic=[value for (year,m),value in totals.items() if m==month and year<current_year]
        current=totals.get((current_year,month))
        rows.append({"month":datetime(2000,month,1).strftime("%b"),"current":round(current,2) if current is not None else None,"historical":round(sum(historic)/len(historic),2) if historic else None,"years":len(historic)})
    return rows
def main():
    rain_all=recent_sensor("CT_Rain_mm",days=None);history=daily_history(rain_all);forecast=noaa_forecast();current={"temperatureF":history[-1]["high"],"timestamp":history[-1]["date"]}
    data={"location":{"name":"UC Davis Campbell Tract","latitude":LAT,"longitude":LON},"updatedAt":datetime.now(timezone.utc).isoformat(),"current":current,"history":history,"forecast":forecast,"monthly":monthly_comparison(rain_all),"sources":{"observed":"UC Davis Weather & Climate Station archive","forecast":"NOAA / National Weather Service API"}}
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,"w") as f:json.dump(data,f,separators=(",",":"))
if __name__=="__main__":main()
