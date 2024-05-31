# Description: Contains utility functions for logging, outputting messages, and taking screenshots

import datetime
import json
import os
import shutil
import sys

# Global variables
dashboard_log = None
output_log = None
output_dir = None


# Creates output directories
def configure_outputs():
    global dashboard_log, output_log, output_dir

    try:
        # Get current date, hour, and minute
        current_datetime = datetime.datetime.now()
        date_str = current_datetime.strftime("%Y-%m-%d_%H-%M")

        # Create output directory with date and time stamp
        output_dir = os.path.join("output", date_str)

        # If the directory already exists, delete it, as it'll be from the exact same timestamp so it's safe to do so
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(os.path.join(output_dir, "overdue"))

        # Create log files
        dashboard_log = open(os.path.join(output_dir, "bot.log"), "a+")
        output_log = open(os.path.join(output_dir, "output.txt"), "a+")

        return output_dir
    except Exception as e:
        print(f"Fatal error: Could not create output files: {e}")
        sys.exit()


# Used for system logging
def log(type, content):
    # Log to console and file
    global dashboard_log, output_log

    if dashboard_log:
        dashboard_log.write(f"{type} - {datetime.datetime.now()}: {content}\n")
        dashboard_log.flush()

    print(f"{type} - {content}")


# Outputs a message against a tutors name
def output(name, text):
    global output_log

    print(f"{name} - {text}")
    output_log.write(f"{name} - {text}\n")
    output_log.flush()


# Takes a screenshot of the active page, naming after the name of the tutor, and assignment number
def screenshot(driver, name, number):

    if driver:
        location = output_dir + "/overdue/"
        driver.driver.save_screenshot(location + name + str(number) + ".png")
    else:
        log("Error", "Could not take screenshot, driver not initialized")


def load_json(filename):
    # Loads a JSON file, returns the keys and values as arrays
    try:
        with open(filename) as file:
            data = json.load(file)
            keys = list(data.keys())
            values = list(data.values())
            return keys, values
    except FileNotFoundError:
        log("Fatal error", f"The {filename} file could not be found")
        sys.exit()
    except json.JSONDecodeError as e:
        log("Fatal error", f"Failed to parse JSON in {filename}: {e}")
        sys.exit()
    except Exception as e:
        log("Fatal error", f"An unexpected error occurred while loading {filename}: {e}")
        sys.exit()