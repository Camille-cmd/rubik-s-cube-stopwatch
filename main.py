#!/usr/bin/env python3

"""A tkinter Rubik's cube stopwatch to send recorded time to Influx db"""

import json
import time
import tkinter as tk
from tkinter import FLAT
from tkinter.font import Font

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.exceptions import InfluxDBError
from influxdb_client.client.write_api import SYNCHRONOUS

RED = "#d55f5e"
BLUE = "#152437"
YELLOWISH = "#f9eacf"


class RubiksCubeStopWatch(tk.Tk):
    """A Tkinter StopWatch to send solving time of a rubik's cube to Influx DB"""

    def __init__(self):
        super().__init__()
        # Get influxdb access config
        self.config = self.get_config()

        # Create Tkinter windows
        self.geometry("300x300")

        # Add image file
        image_bg = tk.PhotoImage(file="rubiks_cube.png")
        # Use a label to display the image in background
        label = tk.Label(self, image=image_bg)
        label.place(x=0, y=0)

        # Bind to the window a key event
        self.bind("<Key>", self.handle_user_event)

        self._start_time = None

        # Create the label to display time
        font_size = Font(self, size=12)
        self.label = tk.Label(
            self, text="Press space to start the stopwatch", bg=YELLOWISH, font=font_size
        )
        self.label.pack()
        # Place the label in the center always
        self.label.place(x=150, y=80, anchor="n")

        # Create a button to send the solving time to influx db
        # It will be .pack() only when the clock is stopped.
        self._final_time = None
        self.influx_btn = tk.Button(
            self,
            text="Send result to InfluxDb",
            bg=RED,
            activebackground=BLUE,
            activeforeground="#FFF",
            command=lambda: self.transmit_to_influxdb(self._final_time)
        )

        # Create a dropdown to select the cube
        self.cube_choice = tk.StringVar(self)

        self.create_widgets()

        # Keep track of the window.after() event identifier to be able to stop it.
        self._after_id = None

        self.mainloop()

    def create_widgets(self):
        """Generate the widgets used in the window"""
        # Create an info label about how to reset
        font_size = Font(self, size=8)
        info_label = tk.Label(
            self, text="Press a to reset the stopwatch", bg=YELLOWISH, font=font_size
        )
        info_label.pack()
        info_label.place(x=150, y=280, anchor="n")

        # Manage the dropdown menu to select the cube
        self.cube_choice.set("speed")  # default value
        cube_options = ("speed", "classic")
        option_menu = tk.OptionMenu(
            self, self.cube_choice, *cube_options
        )
        option_menu.pack(anchor=tk.W, **{'padx': 5, 'pady': 5})
        option_menu.config(
            bg=RED,
            relief=FLAT,
            activebackground=BLUE,
            activeforeground="#FFF",
            cursor="hand1"
        )
        option_menu["menu"].config(
            bg=RED,
            fg="BLACK",
            activebackground=BLUE,
            activeforeground="#FFF"
        )

    @staticmethod
    def get_config():
        """Get the InfluxDb config data"""
        with open("config.json", "r") as f_config:
            return json.load(f_config)

    def start(self):
        """Initiate the timer by keep track of the start point"""
        self._start_time = time.perf_counter()

    def stop(self):
        """Count the time elapsed since the start_time and cancel the after() event on the window"""
        # Cancel the recurring event that display time on the window
        self.after_cancel(self._after_id)

        elapsed_seconds = time.perf_counter() - self._start_time

        # Display the button for the data to be sent to Influxdb
        self._final_time = elapsed_seconds
        self.influx_btn.pack()
        self.influx_btn.place(x=150, y=120, anchor="n")

        str_time = self.format_seconds(elapsed_seconds)
        self.label.configure(text=f"Elapsed time: {str_time} seconds")

    def restart(self):
        """Reset all settings for the stopwatch to start again"""
        self._start_time = None
        self._final_time = None
        # To remove the button, we have to forget every settings
        self.influx_btn.pack_forget()
        self.influx_btn.place_forget()
        self.influx_btn.configure(text="Send result to InfluxDb")
        self.label.configure(text="Hit space to start the stopwatch!")

    def handle_user_event(self, event: tk.Event):
        """
        Manage the user key binding event
        :param event: triggered tkinter event
        """
        # Only start if we have not a start time yet
        if event.keysym == "space" and self._start_time is None:
            self.display_time()
            self.start()

        # Only stop if we have not already recorded a solving time
        elif event.keysym == "space" and not self._final_time:
            self.stop()

        # Reset all recorded data to be able to start/stop again
        elif event.keysym == "a" and self._final_time:
            self.restart()

    def transmit_to_influxdb(self, recorded_seconds: float):
        """
        Send the recorded solving time to influx db
        :param recorded_seconds: elapsed time between start and end in seconds
        """
        if recorded_seconds is not None:
            access_config = {
                "url": self.config["INFLUX_URL"],
                "token": self.config["INFLUX_TOKEN"],
                "org": self.config["INFLUX_ORG"]
            }

            cube_choice = self.cube_choice.get()
            data = (
                Point("solving_time")
                    .tag("cube", cube_choice)
                    .field("recorded_time", recorded_seconds)
            )

            with InfluxDBClient(**access_config) as _client:
                with _client.write_api(write_options=SYNCHRONOUS) as _write_client:
                    try:
                        _write_client.write(bucket=self.config["INFLUX_BUCKET"], record=data)
                        self.influx_btn.configure(text="Data sent to InfluxDb!")
                    except InfluxDBError as ex:
                        self.label.configure(text=ex)

    @staticmethod
    def format_seconds(seconds: float):
        """
        Transform seconds into hour:minute:second.milliseconds format
        :param seconds: elapsed time between start and end in seconds
        """
        miliseconds = str(seconds).split(".")[1][:3]
        str_time = time.strftime("%H:%M:%S", time.gmtime(seconds))
        str_time += f'.{miliseconds}'

        return str_time

    def display_time(self):
        """Change the text of the label to display passing time"""
        text = "Starting...."
        if self._start_time is not None:
            elapsed_seconds = time.perf_counter() - self._start_time
            converted_time = self.format_seconds(elapsed_seconds)
            text = converted_time

        self.label.configure(text=text)

        # Repeat the display time event every 1s
        self._after_id = self.after(20, self.display_time)


if __name__ == "__main__":
    RubiksCubeStopWatch()
