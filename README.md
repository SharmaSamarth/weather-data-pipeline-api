Weather Data Pipeline & FastAPI Service

A Python-based weather project that demonstrates REST API integration, synchronous and asynchronous requests, JSON parsing, data transformation, Pandas data processing, validation, and report generation.

The project contains two parts:

Weather Data Pipeline – fetches weather data for multiple cities, processes it with Pandas, validates the data, and exports reports.

Weather API Server – exposes weather information through FastAPI REST endpoints and supports both single-city and batch requests.

Project Architecture

flowchart TD
    A[City Names] --> B[Open-Meteo Geocoding API]
    B --> C[Latitude & Longitude]
    C --> D[Open-Meteo Weather API]
    D --> E[JSON Response]
    E --> F[Parse & Transform Data]
    F --> G[Pandas DataFrame]
    G --> H[Clean & Validate Data]
    H --> I[Derived Fields]
    I --> J[Export Reports]
    J --> K[CSV]
    J --> L[Excel]
    J --> M[JSON]

Weather Data Pipeline Flow

flowchart TD
    A[Start] --> B[Load Configured Cities]
    B --> C[Geocode City]
    C --> D{Coordinates Found?}
    D -- No --> E[Record City as Failed]
    E --> C
    D -- Yes --> F[Fetch Current Weather]
    F --> G{Weather Request Successful?}
    G -- No --> H[Record City as Failed]
    H --> C
    G -- Yes --> I[Parse JSON]
    I --> J[Flatten Weather Record]
    J --> K[Collect Records]
    K --> L[Create Pandas DataFrame]
    L --> M[Clean & Validate Data]
    M --> N[Create Derived Fields]
    N --> O[Sort Data]
    O --> P[Save CSV / Excel / JSON]
    P --> Q[End]

FastAPI Request Flow

flowchart LR
    A[Client] --> B[FastAPI]
    B --> C{Endpoint}
    C -->|GET /weather/{city}| D[Geocode City]
    C -->|GET /weather-batch?cities=...| E[Create Async Tasks]
    D --> F[Fetch Weather]
    F --> G[Transform Data]
    G --> H[Validate Data]
    H --> I[JSON Response]
    E --> J[Concurrent API Requests]
    J --> K[Transform Results]
    K --> L[Validate Results]
    L --> M[Pandas DataFrame]
    M --> N[Export Reports]
    N --> O[JSON Response]

Features

Fetch current weather for individual cities

Fetch weather for multiple cities concurrently

City-name geocoding using Open-Meteo

Synchronous HTTP requests using requests

Asynchronous HTTP requests using httpx

Concurrent processing with asyncio.gather()

JSON parsing and flattening

Pandas DataFrame transformation

Data cleaning and validation

Celsius-to-Fahrenheit conversion

Duplicate and incomplete record handling

CSV, Excel, and JSON report generation

FastAPI REST endpoints

Interactive API documentation through FastAPI /docs

Technologies Used

Technology

Purpose

Python

Core programming language

FastAPI

REST API development

Uvicorn

ASGI server for FastAPI

Requests

Synchronous HTTP requests

HTTPX

Asynchronous HTTP requests

Asyncio

Concurrent execution

Pandas

Data processing and transformation

OpenPyXL

Excel report generation

Open-Meteo

Weather and geocoding APIs

Project Structure

weather-project/
│
├── weather_api_server.py
├── weather_data_pipeline.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── output/
    ├── weather_report.csv
    ├── weather_report.xlsx
    └── weather_report.json

The output/ directory contains generated reports and can be excluded from Git using .gitignore.

1. Weather Data Pipeline

The standalone pipeline processes weather information for a configured list of cities.

Pipeline Steps

City Names
    ↓
Geocoding API
    ↓
Coordinates
    ↓
Weather API
    ↓
JSON Response
    ↓
Transformation
    ↓
Pandas DataFrame
    ↓
Cleaning & Validation
    ↓
Derived Fields
    ↓
CSV / Excel / JSON

Run the Pipeline

python weather_data_pipeline.py

The pipeline saves:

output/weather_report.csv
output/weather_report.xlsx
output/weather_report.json

2. Weather API Server

The FastAPI service provides weather information through REST endpoints.

Start the Server

uvicorn weather_api_server:app --reload

The API will be available at:

http://127.0.0.1:8000

Interactive Swagger documentation:

http://127.0.0.1:8000/docs

API Endpoints

Get Weather for One City

GET /weather/{city}

Example:

GET /weather/Bangalore

Get Weather for Multiple Cities

GET /weather-batch?cities=Bangalore,Mumbai,Delhi,Chennai

The batch endpoint processes multiple cities concurrently and returns requested cities, successful records, failed records, processing time, processed weather data, and generated report paths.

Data Processing

The project converts nested API responses into a simpler structure.

Example

Raw API Response
      ↓
{
  latitude: ...,
  longitude: ...,
  current: {
      temperature_2m: ...,
      wind_speed_10m: ...,
      weather_code: ...,
      time: ...
  }
}
      ↓
Flattened Record
      ↓
{
  city: ...,
  latitude: ...,
  longitude: ...,
  temperature_c: ...,
  windspeed_kmh: ...,
  weather_code: ...,
  observed_at: ...
}

Data Validation

The project validates weather records before returning or exporting them.

Examples:

Required city and location information must be present

Temperature must be within the configured sanity range

Wind speed cannot be negative

Duplicate cities are removed

Records with missing essential data are removed

Synchronous vs Asynchronous Processing

Synchronous

Used by:

GET /weather/{city}

Requests are performed sequentially.

Request 1 → Response
             ↓
Request 2 → Response
             ↓
Request 3 → Response

Asynchronous

Used by:

GET /weather-batch?cities=...

Multiple city requests can run concurrently.

City A ─┐
City B ─┼──→ Concurrent Requests
City C ─┤
City D ─┘
             ↓
       Combined Results

Error Handling

The application handles common external API and data-processing failures, including:

City not found

HTTP/API request failures

Invalid API responses

Missing data

Invalid weather values

Failed cities in batch requests

Installation

1. Clone the Repository

git clone <your-repository-url>
cd <repository-name>

2. Create a Virtual Environment

python -m venv venv

3. Activate the Virtual Environment

Windows

venv\Scripts\activate

macOS / Linux

source venv/bin/activate

4. Install Dependencies

pip install -r requirements.txt

Configuration

The current implementation uses Open-Meteo APIs and does not require an API key for this use case.

API endpoints used by the project:

https://geocoding-api.open-meteo.com/v1/search
https://api.open-meteo.com/v1/forecast

Learning Objectives

This project demonstrates practical knowledge of:

REST API consumption

Synchronous and asynchronous programming

Concurrent API requests

JSON parsing

Data transformation

Pandas

Data validation

FastAPI

Error handling

File generation and export

API documentation

Example End-to-End Workflow

flowchart TD
    A[User / Scheduled Run] --> B[City List]
    B --> C[Geocoding API]
    C --> D[Coordinates]
    D --> E[Weather API]
    E --> F[JSON Data]
    F --> G[Transform]
    G --> H[Validate]
    H --> I{Valid Data?}
    I -- No --> J[Handle / Report Failure]
    I -- Yes --> K[Pandas Processing]
    K --> L[Generate Reports]
    L --> M[CSV]
    L --> N[Excel]
    L --> O[JSON]


