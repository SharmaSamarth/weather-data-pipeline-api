"""
Weather API Server
=======================================

Use case:
    A website provides weather information for multiple cities.

    This FastAPI service demonstrates:

        1. Synchronous API consumption using requests.
        2. Asynchronous API consumption using httpx.
        3. JSON parsing.
        4. Data transformation.
        5. Pandas data manipulation.
        6. Data validation.
        7. CSV / Excel / JSON export.
        8. FastAPI REST endpoints.

"""

import asyncio
import time
from pathlib import Path

import httpx
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException


# FASTAPI APPLICATION

app = FastAPI(
    title="Day 9 Weather Service",
    description=(
        "Weather API demonstrating REST calls, "
        "async processing, Pandas transformation, "
        "validation and file export."
    ),
    version="1.0.0",
)


# CONFIGURATION

GEOCODE_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

REQUEST_TIMEOUT = 10

OUTPUT_DIR = Path("output")


# JSON PARSING / TRANSFORMATION

def flatten_weather_record(
    city_name: str,
    raw_data: dict,
) -> dict:
    """
    Convert nested weather JSON into a flat dictionary.
    """

    current = raw_data.get(
        "current",
        {},
    )

    temperature = current.get(
        "temperature_2m"
    )

    windspeed = current.get(
        "wind_speed_10m"
    )

    return {
        "city": city_name.strip().title(),
        "latitude": raw_data.get("latitude"),
        "longitude": raw_data.get("longitude"),
        "temperature_c": temperature,
        "windspeed_kmh": windspeed,
        "weather_code": current.get("weather_code"),
        "observed_at": current.get("time"),
        "temperature_f": (
            round(
                (temperature * 9 / 5) + 32,
                1,
            )
            if temperature is not None
            else None
        ),
    }


# DATA VALIDATION

def validate_weather_records(
    records: list[dict],
) -> list[dict]:
    """
    Validate API records before sending them
    into Pandas.
    """

    valid_records = []

    for record in records:

        # Required fields
        if not record.get("city"):
            continue

        if record.get("temperature_c") is None:
            continue

        if record.get("latitude") is None:
            continue

        if record.get("longitude") is None:
            continue

        # Temperature sanity check
        temperature = record["temperature_c"]

        if not -50 <= temperature <= 60:
            continue

        # Wind speed sanity check
        windspeed = record.get("windspeed_kmh")

        if windspeed is not None and windspeed < 0:
            continue

        valid_records.append(record)

    return valid_records


# PANDAS DATAFRAME

def create_dataframe(
    records: list[dict],
) -> pd.DataFrame:
    """
    Convert validated records into a Pandas DataFrame.
    """

    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Convert numeric fields
    numeric_columns = [
        "latitude",
        "longitude",
        "temperature_c",
        "temperature_f",
        "windspeed_kmh",
        "weather_code",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # Remove duplicate cities
    df = df.drop_duplicates(
        subset=["city"],
    )

    # Remove records with missing essential data
    df = df.dropna(
        subset=[
            "temperature_c",
            "latitude",
            "longitude",
        ]
    )

    # Sort by temperature
    df = df.sort_values(
        by="temperature_c",
        ascending=False,
    )

    # Reset index
    df = df.reset_index(
        drop=True
    )

    return df


# FILE EXPORT

def export_weather_report(
    df: pd.DataFrame,
) -> dict:
    """
    Save the processed weather data into:

        CSV
        Excel
        JSON
    """

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    csv_path = (
        OUTPUT_DIR
        / "weather_report.csv"
    )

    excel_path = (
        OUTPUT_DIR
        / "weather_report.xlsx"
    )

    json_path = (
        OUTPUT_DIR
        / "weather_report.json"
    )

    # CSV
    df.to_csv(
        csv_path,
        index=False,
    )

    # Excel
    df.to_excel(
        excel_path,
        index=False,
        sheet_name="Weather",
    )

    # JSON
    df.to_json(
        json_path,
        orient="records",
        indent=2,
    )

    return {
        "csv": str(csv_path),
        "excel": str(excel_path),
        "json": str(json_path),
    }


# SINGLE CITY - SYNCHRONOUS VERSION

@app.get("/weather/{city}")
def get_weather(
    city: str,
):
    """
    Fetch weather for one city synchronously.

    Uses:
        requests
        JSON parsing
        transformation
    """

    try:

        
        # Step 1 - Get coordinates
        

        geo_response = requests.get(
            GEOCODE_URL,
            params={
                "name": city,
                "count": 1,
                
            },
            timeout=REQUEST_TIMEOUT,
        )

        geo_response.raise_for_status()

        geo_data = geo_response.json()

        results = geo_data.get(
            "results"
        )

        if not results:

            raise HTTPException(
                status_code=404,
                detail=f"City not found: {city}",
            )

        location = results[0]

        latitude = location["latitude"]
        longitude = location["longitude"]

        
        # Step 2 - Get current weather
        

        weather_response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                ),
            },
            timeout=REQUEST_TIMEOUT,
        )

        weather_response.raise_for_status()

        weather_data = (
            weather_response.json()
        )

        
        # Step 3 - Transform
        

        record = flatten_weather_record(
            city,
            weather_data,
        )

        
        # Step 4 - Validate
        

        valid_records = (
            validate_weather_records(
                [record]
            )
        )

        if not valid_records:

            raise HTTPException(
                status_code=500,
                detail="Weather data failed validation.",
            )

        return valid_records[0]

    except HTTPException:
        raise

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Weather API request failed: {exc}",
        ) from exc


# ASYNC CITY FETCH

async def fetch_one_city(
    client: httpx.AsyncClient,
    city: str,
) -> dict:
    """
    Fetch one city asynchronously.

    This function is used by asyncio.gather()
    so multiple cities can be fetched concurrently.
    """

    try:

        
        # Step 1 - Geocoding
        

        geo_response = await client.get(
            GEOCODE_URL,
            params={
                "name": city,
                "count": 1,
                
            },
        )

        geo_response.raise_for_status()

        geo_data = geo_response.json()

        results = geo_data.get(
            "results"
        )

        if not results:

            return {
                "city": city,
                "error": "City not found",
            }

        location = results[0]

        latitude = location["latitude"]
        longitude = location["longitude"]

        
        # Step 2 - Weather
        

        weather_response = await client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                ),
            },
        )

        weather_response.raise_for_status()

        weather_data = (
            weather_response.json()
        )

        
        # Step 3 - Transform
        

        return flatten_weather_record(
            city,
            weather_data,
        )

    except httpx.HTTPError as exc:

        return {
            "city": city,
            "error": str(exc),
        }

    except (KeyError, TypeError) as exc:

        return {
            "city": city,
            "error": f"Invalid API response: {exc}",
        }


# ASYNC BATCH ENDPOINT
# IMPORTANT:
# This route appears BEFORE /weather/{city}

@app.get("/weather-batch")
async def get_weather_batch(
    cities: str,
):
    """
    Fetch multiple cities concurrently.

    Example:

        /weather-batch
        ?cities=Bangalore,Mumbai,Delhi,Chennai,Himachal
    """

    city_list = [
        city.strip()
        for city in cities.split(",")
        if city.strip()
    ]

    if not city_list:

        raise HTTPException(
            status_code=400,
            detail=(
                "Provide at least one city "
                "using ?cities="
            ),
        )

    start_time = time.perf_counter()

    
    # Create ONE shared async client
    

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT
    ) as client:

        
        # Create tasks
        

        tasks = [
            fetch_one_city(
                client,
                city,
            )
            for city in city_list
        ]

        
        # Run all city requests concurrently
        

        results = await asyncio.gather(
            *tasks
        )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    
    # Separate successful and failed results
    

    successful_records = [
        result
        for result in results
        if "error" not in result
    ]

    failed_records = [
        result
        for result in results
        if "error" in result
    ]

    
    # Validate records
    

    valid_records = (
        validate_weather_records(
            successful_records
        )
    )

    
    # Create Pandas DataFrame
    

    df = create_dataframe(
        valid_records
    )

    if df.empty:

        raise HTTPException(
            status_code=500,
            detail=(
                "No valid weather records "
                "were available."
            ),
        )

    
    # Export report
    

    exported_files = (
        export_weather_report(df)
    )

    
    # Return API response
    

    return {
        "requested_cities": city_list,
        "successful_records": len(
            valid_records
        ),
        "failed_records": failed_records,
        "elapsed_seconds": round(
            elapsed,
            2,
        ),
        "exported_files": exported_files,
        "data": df.to_dict(
            orient="records"
        ),
    }


# ROOT ENDPOINT

@app.get("/")
def root():
    return {
        "message": "Day 9 Weather Service is running.",
        "endpoints": [
            "/weather/Bangalore",
            (
                "/weather-batch"
                "?cities=Bangalore,Mumbai,"
                "Delhi,Chennai,Himachal"
            ),
            "/docs",
        ],
    }