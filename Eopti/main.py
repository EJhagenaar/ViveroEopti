from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, StreamingResponse
from functions import Eoptimization
import uvicorn
import yaml, json
from datetime import datetime,timedelta,date
import pandas as pd

#Import configuration file
config='json'
if config=='json':
    try:
        file=open('data/options.json')
        config = json.load(file)
    except ValueError:
        print('Loading JSON has failed')

else:
    with open("config.yaml", "r") as stream:
        try:
            config=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

Eopti=Eoptimization(config)
app = FastAPI()

@app.get("/")
def root():
    return [{"Status": "Vivero E-optimization is online"},
            {"Error Codes": "None"},
    ]

@app.get("/calculate")
def calculate():
    try:
        Eopti.loadPVForecast()
    except Exception as error:
        return {"status": "Error trying to load PV Forecast"}, error
   
    try:
        Eopti.loadPrices()
    except Exception as error:
        return {"status": "Error trying to load prices from entso-e platform"}, error
    
    try:
        Eopti.getTempForecast()
    except Exception as error:
        return {"status": "Error trying to get temperature forecast from OpenWeatherMap"}, error

    try:
        Eopti.loadEdata()
        print('excecuted Eopti.loadEdata()')
    except Exception as error:
        # handle the exception
        return {"status": "Error trying to load historical energy data from HA sensor and influxDB"}, error
    
    try:
        Eopti.getExogFut(temp=1)
        print('excecuted getExogFut()')
    except Exception as error:
        return {"status": "Error trying to get future external variables"}, error

    try:
        Eopti.forecastEdata(backtest=0,plot=0)
        print('excecuted Eopti.forecastEdata(backtest=0,plot=0)')
    except Exception as error:
        return {"status": "Error trying to create forecast data for energy"}, error
    
    try:
        Eopti.createOptInput()
    except Exception as error:
        return {"status": "Error trying to greate dataframe from previous input"}, error

    try:
        Eopti.priceForecast()
    except Exception as error:
        return {"status": "Error trying to get price forecast >24h ahead from "}, error
    
    try:
        Eopti.createOptimization(smartSOC=1)
    except Exception as error:
        return {"status": "Error trying to greate dataframe from previous input"}, error
   
    return Response(Eopti.Optimization.to_json(orient="index"), media_type="application/json")

@app.get("/plot/{number}")
def plot(number):
    try:
        buf=Eopti.plotOptimization(plot=int(number))
    except:
        return {"status": "Error trying to greate dataframe from previous input"} 
    
    return StreamingResponse(buf, media_type="image/png")

@app.get("/current/{entity}")
def current(entity):
    if len(Eopti.Optimization.index)>0:
        df=Eopti.Optimization
        df=df[(df.index.date == date.today()) & (df.index.hour == datetime.now().hour) ]
        return {"status": "success", "data": {entity: df[entity].values[0]},"message": "null"}

@app.get("/forecast/{entity}")
def forecast(entity):
    df=Eopti.Optimization
    df=df[[entity]]
    data=[]
    for index, row in df.iterrows():
        data.append({'time': index, entity: row[entity]})
    return {"status": "success", "data": data,"message": "null"}

@app.get("/actuals/{entity}")
def actuals(entity):
    Eopti.getActuals(entity)
    df=Eopti.Optimization
    df=df[[entity]]
    data=[]
    for index, row in df.iterrows():
        data.append({'time': index, entity: row[entity]})
    return {"status": "success", "data": data,"message": "null"}  


                

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
