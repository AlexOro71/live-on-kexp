#!/usr/bin/env python3
"""
KEXP Now Playing Display
Main application for displaying current show and now playing on RGB LED matrix
"""

import time
import logging
from datetime import datetime
from display.renderer import DisplayRenderer
from kexp.api_client import KEXPClient
from weather_client import WeatherClient
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KEXPDisplay:
    def __init__(self, config):
        self.config = config
        self.kexp_client = KEXPClient()
        self.weather_client = WeatherClient(
            getattr(config, 'weather_lat', 47.5301),
            getattr(config, 'weather_lon', -122.0326)
        )
        self.renderer = DisplayRenderer(config)
        self.current_play = None
        self.current_weather = None

    def fetch_new_data(self):
        """Fetch latest data from KEXP API"""
        try:
            # Get current play (now playing)
            play_data = self.kexp_client.get_current_play()

            if play_data and play_data != self.current_play:
                # Always fetch show details if we have a show ID
                # This is used for color scheme selection
                if play_data.get('show'):
                    show_details = self.kexp_client.get_show_details(play_data['show'])
                    if show_details:
                        play_data['show_name'] = show_details.get('program_name', 'KEXP')
                        # host_names is a list, join it into a string
                        host_names = show_details.get('host_names', [])
                        if isinstance(host_names, list):
                            play_data['host_name'] = ', '.join(host_names) if host_names else ''
                        else:
                            play_data['host_name'] = host_names or ''

                # Append Album and Release Year to the song string for scrolling
                if play_data.get('play_type') != 'airbreak':
                    album = play_data.get('album')
                    release_date = play_data.get('release_date')
                    year = str(release_date)[:4] if release_date else ''
                    song_title = play_data.get('song', '')

                    if album and year:
                        play_data['song'] = f"{song_title} [{album} ({year})]"
                    elif album:
                        play_data['song'] = f"{song_title} [{album}]"
                    elif year:
                        play_data['song'] = f"{song_title} ({year})"

                self.current_play = play_data

                if play_data.get('play_type') == 'airbreak':
                    logger.info(f"Air break: {play_data.get('show_name', 'KEXP')}")
                else:
                    show_name = play_data.get('show_name', 'KEXP')
                    logger.info(f"Now playing: {play_data['artist']} - {play_data['song']} ({show_name})")

        except Exception as e:
            logger.error(f"Error fetching data: {e}")

    def run(self):
        """Main loop"""
        logger.info("KEXP Display started")

        # Fetch initial KEXP and weather data
        self.fetch_new_data()
        self.current_weather = self.weather_client.get_weather()

        last_fetch_time = time.time()
        last_weather_time = time.time()
        last_clock_time = time.time()
        showing_clock = False
        clock_start_time = 0
        frame_delay = 0.08  # Slightly faster scrolling (~12.5 FPS)

        # Configurable intervals (with fallback defaults)
        clock_interval = getattr(self.config, 'clock_interval', 60)
        clock_duration = getattr(self.config, 'clock_duration', 5)
        weather_interval = getattr(self.config, 'weather_interval', 900)

        try:
            while True:
                current_time = time.time()

                # Fetch new KEXP data periodically
                if current_time - last_fetch_time >= self.config.update_interval:
                    self.fetch_new_data()
                    last_fetch_time = current_time

                # Refresh weather periodically
                if current_time - last_weather_time >= weather_interval:
                    new_weather = self.weather_client.get_weather()
                    if new_weather:
                        self.current_weather = new_weather
                    last_weather_time = current_time

                # Check if it is time to trigger the date/time/weather display
                if not showing_clock and (current_time - last_clock_time >= clock_interval):
                    showing_clock = True
                    clock_start_time = current_time

                # Check if the date/time/weather display duration has finished
                if showing_clock and (current_time - clock_start_time >= clock_duration):
                    showing_clock = False
                    last_clock_time = current_time

                # Render either the date/time/weather or the current KEXP play
                if showing_clock:
                    try:
                        now = datetime.now()
                        if self.current_weather:
                            # Compact top row so date + time fit cleanly with weather below
                            time_short = now.strftime("%I:%M%p").lstrip("0").lower().replace("m", "")
                            top_str = f"{now.strftime('%b %d')} {time_short}"
                            self.renderer.render_datetime(top_str, self.current_weather)
                        else:
                            # Fallback if weather API is unreachable
                            date_str = now.strftime("%a %b %d")
                            time_str = now.strftime("%I:%M %p").lstrip("0")
                            self.renderer.render_datetime(date_str, time_str)
                    except Exception as e:
                        logger.error(f"Error rendering date/time/weather: {e}")
                elif self.current_play:
                    try:
                        self.renderer.render_now_playing(self.current_play)
                    except Exception as e:
                        logger.error(f"Error in render loop: {e}")
                        pass

                time.sleep(frame_delay)

        except KeyboardInterrupt:
            logger.info("KEXP Display stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.renderer.cleanup()


def main():
    config = Config()
    display = KEXPDisplay(config)
    display.run()


if __name__ == "__main__":
    main()
