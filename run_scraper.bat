@echo off
:: Navigate to the project folder
cd /d "%~dp0"

:: Activate the Virtual Environment
call venv\Scripts\activate

:: Run the Scraper
echo Running MarketPulse Scraper...
python main.py

:: Keep window open for 10 seconds to see results
timeout /t 10