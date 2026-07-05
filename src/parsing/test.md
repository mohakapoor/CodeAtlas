# WeatherCLI

WeatherCLI is a blazing fast command-line tool that fetches real-time weather data directly to your terminal.

## Features

- Real-time temperature and precipitation forecasts.
- Auto-detects your location based on IP address.
- Custom color themes for the terminal output.

## Installation

You can install the tool globally using npm or yarn:

```bash
npm install -g weather-cli
```

### Authentication

Before you can use WeatherCLI, you must configure it with a valid API key from OpenWeatherMap.

1. Create an account at [OpenWeatherMap](https://openweathermap.org).
2. Generate a free API key.
3. Add it to your configuration:

```bash
weather-cli config set api_key="YOUR_KEY_HERE"
```

## Usage

Simply type `weather` in your terminal to get the current forecast for your detected location.

```javascript
// You can also import it directly into a Node.js script
const weather = require('weather-cli');

weather.getForecast('London').then(data => {
    console.log(data.temperature);
});
```
