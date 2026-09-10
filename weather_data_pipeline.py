"""
 Weather Data Pipeline
==========================================

Use case:
    Needs a periodic weather report for multiple cities.

    This script:
        1. Fetches city coordinates from Open-Meteo's geocoding API.
        2. Fetches current weather data from the Open-Meteo weather API.
        3. Parses and flattens the nested JSON response.
        4. Loads the records into Pandas.
        5. Cleans and validates the data.
        6. Creates derived fields.
        7. Saves the final report as CSV, Excel and JSON.

Run:
    python weather_data_pipeline.py

Requires internet access.
Open-Meteo does not require an API key for this use case.
"""

import sys
import time
from pathlib import Path
from typing import Optional
import truststore
truststore.inject_into_ssl()

import pandas as pd

import requests

# CONFIGURATION

CITIES = [
    "Bangalore",
    "Shimla",
    "Mumbai",
    "Delhi",
    "Chennai",
    "Nowhereville",
]

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 10

OUTPUT_DIR = Path("output")


# STEP 1 - GEOCODE CITY

def geocode_city(city_name: str) -> Optional[dict]:
    """
    Convert a city name into latitude and longitude.
    """

    try:
        response = requests.get(
            GEOCODE_URL,
            params={
                "name": city_name,
                "count": 1,
                
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results")

        if not results:
            print(f"  [NOT FOUND] {city_name}")
            return None

        top_result = results[0]

        return {
            "latitude": top_result["latitude"],
            "longitude": top_result["longitude"],
        }

    except requests.RequestException as exc:
        print(f"  [GEOCODING ERROR] {city_name}: {exc}")
        return None

    except (KeyError, TypeError):
        print(f"  [INVALID RESPONSE] Could not read coordinates for {city_name}")
        return None


# STEP 2 - FETCH CURRENT WEATHER

def fetch_current_weather(
    latitude: float,
    longitude: float,
) -> Optional[dict]:
    """
    Fetch current weather for a latitude/longitude pair.
    """

    try:
        response = requests.get(
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

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        print(
            f"  [WEATHER API ERROR] "
            f"({latitude}, {longitude}): {exc}"
        )
        return None


# STEP 3 - JSON PARSING AND TRANSFORMATION

def flatten_weather_record(
    city_name: str,
    raw_data: dict,
) -> dict:
    """
    Convert nested API JSON into one flat record.

    Raw structure:
        {
            "latitude": ...,
            "longitude": ...,
            "current": {
                "temperature_2m": ...,
                "wind_speed_10m": ...,
                "weather_code": ...,
                "time": ...
            }
        }

    Flat structure:
        {
            "city": ...,
            "latitude": ...,
            "longitude": ...,
            "temperature_c": ...,
            "windspeed_kmh": ...,
            "weather_code": ...,
            "observed_at": ...
        }
    """

    current = raw_data.get("current", {})

    return {
        "city": city_name.strip().title(),
        "latitude": raw_data.get("latitude"),
        "longitude": raw_data.get("longitude"),
        "temperature_c": current.get("temperature_2m"),
        "windspeed_kmh": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "observed_at": current.get("time"),
    }


# STEP 4 - COLLECT ALL WEATHER RECORDS

def collect_weather_records(
    cities: list[str],
) -> tuple[list[dict], list[str]]:
    """
    Fetch weather for every requested city.

    Returns:
        records -> successful weather records
        failed  -> cities that could not be processed
    """

    records = []
    failed = []

    for city in cities:

        print(f"Fetching: {city}")

        coordinates = geocode_city(city)

        if coordinates is None:
            failed.append(city)
            continue

        weather_data = fetch_current_weather(
            coordinates["latitude"],
            coordinates["longitude"],
        )

        if weather_data is None:
            failed.append(city)
            continue

        record = flatten_weather_record(
            city,
            weather_data,
        )

        records.append(record)

    return records, failed


# STEP 5 - PANDAS + DATA VALIDATION + CLEANING

def build_dataframe(records: list[dict]) -> pd.DataFrame:
    """
    Convert records to a DataFrame and clean/validate the data.
    """

    df = pd.DataFrame(records)

    if df.empty:
        return df

    print("\nRaw DataFrame:")
    print(df)

    
    # Convert numeric fields to numeric data types
    # Invalid values become NaN instead of crashing the script.
    

    numeric_columns = [
        "latitude",
        "longitude",
        "temperature_c",
        "windspeed_kmh",
        "weather_code",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    
    # Remove duplicate cities
    

    before_duplicates = len(df)

    df = df.drop_duplicates(
        subset=["city"],
    )

    duplicates_removed = (
        before_duplicates - len(df)
    )

    if duplicates_removed:
        print(
            f"Removed {duplicates_removed} duplicate record(s)."
        )

    
    # Remove rows where essential fields are missing
    

    before_missing = len(df)

    df = df.dropna(
        subset=[
            "city",
            "temperature_c",
            "latitude",
            "longitude",
        ]
    )

    missing_removed = (
        before_missing - len(df)
    )

    if missing_removed:
        print(
            f"Removed {missing_removed} "
            f"record(s) with missing required data."
        )

    
    # Validate temperature range
    

    df["is_suspect"] = (
        (df["temperature_c"] < -50)
        | (df["temperature_c"] > 60)
    )

    
    # Validate wind speed
    

    df["invalid_wind_speed"] = (
        df["windspeed_kmh"] < 0
    )

    
    # Derived field:
    # Celsius -> Fahrenheit
    

    df["temperature_f"] = (
        df["temperature_c"] * 9 / 5 + 32
    ).round(1)

    
    # Sort hottest -> coldest
    

    df = df.sort_values(
        by="temperature_c",
        ascending=False,
    )

    
    # Reset index
    

    df = df.reset_index(drop=True)

    return df


# STEP 6 - SAVE REPORT

def save_report(
    df: pd.DataFrame,
    base_filename: str = "weather_report",
) -> None:
    """
    Save the processed DataFrame as:
        CSV
        Excel
        JSON
    """

    if df.empty:
        print("Nothing to save. DataFrame is empty.")
        return

    OUTPUT_DIR.mkdir(
        exist_ok=True,
    )

    csv_path = OUTPUT_DIR / f"{base_filename}.csv"
    excel_path = OUTPUT_DIR / f"{base_filename}.xlsx"
    json_path = OUTPUT_DIR / f"{base_filename}.json"

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

    print("\nFiles saved successfully:")
    print(f"CSV   : {csv_path}")
    print(f"Excel : {excel_path}")
    print(f"JSON  : {json_path}")


# STEP 7 - MAIN

def main() -> None:

    start_time = time.perf_counter()

    print("=" * 60)
    print("DAY 9 - WEATHER DATA PIPELINE")
    print("=" * 60)

    print(
        f"\nFetching weather for {len(CITIES)} cities...\n"
    )

    records, failed = collect_weather_records(CITIES)

    print("\n" + "-" * 60)

    print(
        f"Successful records: {len(records)}"
    )

    print(
        f"Failed cities: {len(failed)}"
    )

    if failed:
        print(
            f"Failed city list: {failed}"
        )

    # Build Pandas DataFrame
    df = build_dataframe(records)

    print("\n" + "-" * 60)

    print("FINAL PROCESSED DATA")
    print("-" * 60)

    if df.empty:
        print("No valid records available.")
    else:
        print(df.to_string(index=False))

    # Save files
    save_report(df)

    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 60)

    print(
        f"Pipeline completed in {elapsed:.2f} seconds."
    )

    print("=" * 60)


# PROGRAM ENTRY POINT

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nPipeline stopped by user.")
        sys.exit(1)