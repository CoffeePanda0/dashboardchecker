# Credits - Alexander Thomas (CoffeePanda)
# This software is property of Wolsey Hall Oxford and is not to be distributed without permission

VERSION = "2.B" 


# -- INCLUDES --
import datetime
import time
import json
import datetime
import os
import sys
import shutil

from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Local module imports
import checker


# -- CONSTANTS --
CANVAS_URL = "https://wolseyhalloxford.instructure.com" # Canvas URL eg https://abc.infastructure.com
OVERDUE_LENGTH = 5 # How many either hours / days since submission until the assigmment is overdue
USE_HOURS = False # If True, uses hours since submission. If False, uses calendar days
TIMEOUT = 10 # How many seconds (maximum) to wait for a large assignment to load


# -- GLOBAL VARIABLES -- 
dashboard_log = None # Used for dashboardchecker usage related logs (runtime errors, etc)
output_log = None # Used for outputting the results of the dashboardchecker
driver = None # Selenium driver
output_dir = None


# -- CHROME DRIVER OPTIONS --
options_array = [
    "--ignore-certificate-error",
    "--ignore-ssl-errors",
    "--headless",
    "--incognito",
    "window-size=1920,1080"
]

# Holds information about a tutor, and all of their assignments
class Tutor:

    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.overdue_time_since_submission = [] # List of overdue time since submission for each assignment. This is either hours or days
        self.calendar_days_since_submission = [0] * 13 # List of calendar days since submission for each assignment. 0-11, 12+
        self.hours_since_submission = [] # List of hours since submission for each assignment


    # Adds an assignment to the list
    def add_assignment(self, hours_since_submission, calendar_days_since_submission, overdue):
        global USE_HOURS

        self.hours_since_submission.append(hours_since_submission)
        if calendar_days_since_submission < 12:
            self.calendar_days_since_submission[calendar_days_since_submission] += 1
        else:
            self.calendar_days_since_submission[12] += 1

        if overdue:
            if USE_HOURS:
                self.overdue_time_since_submission.append(hours_since_submission)
            else:
                self.overdue_time_since_submission.append(calendar_days_since_submission)


    # Returns the number of overdue assignments
    def get_overdue(self):
        # Calculates the number of overdue assignments
        return len(self.overdue_time_since_submission)


    # Returns average hours that have passed since submission
    def get_average_hours(self):
        # Returns the average from the hours_since_submission, then rounds to the nearest hour
        return round(sum(self.hours_since_submission) / len(self.hours_since_submission))


# -- FUNCTIONS --

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


def screenshot(name, number):
    # Takes a screenshot of the active page
    global driver
 
    if driver:
        location = output_dir + "/overdue/"
        driver.save_screenshot(location + name + str(number) + ".png")
    else:
        log("Error", "Could not take screenshot, driver not initialized")





def load_tutors(filename):
    # Loads JSON file contatining all tutors, returns the keys (names) and values (id)

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
    

def act_as_user(user_id, user_name):
    # Act as a user given their ID. Return True if successful, False otherwise
    global driver, CANVAS_URL, TIMEOUT

    driver.get(CANVAS_URL + f"/users/{user_id}/masquerade")
    try:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.LINK_TEXT, "Proceed")))
        proceed_button = driver.find_element(By.LINK_TEXT, "Proceed")
        proceed_button.click()
    except:
        log("Act as user - Error", f"You do not have permission to act as {user_name}")
        return False
    
    if driver.title == "Dashboard":
        log("Act as user - Success", f"Acting as user {user_name}")
        return True
    else:
        log("Act as user - Error", f"Could not act as user {user_name}")
        return False


def strip_date_string(date_string):
    # Check first for any anomalies in the date string

    if "missing" in date_string:
        log("Warning", f"Could not calculate time since submission: Assignment is marked MISSING")
        return ""
    elif "no submission time" in date_string:
        log("Warning", f"Could not calculate time since submission: No submission time")
        return ""

    # Process the date string to remove unnecessary text
    date_string = date_string.replace("Submitted:\n", "").replace("at ", "").rstrip().replace("\n", "")

    # Remove the year from the date string (if it exists), as we want to format it ourselves
    contains_year = 0
    for i in range (0, 5):
        last_year = str(datetime.datetime.now().year - i)
        if last_year in date_string:
            date_string = date_string.replace(last_year, "")
            contains_year = i
            break

    # Format by adding the year at the start for easier comparison between formats
    formatted_timestamp = str(datetime.datetime.now().year - contains_year) + " " + date_string
    return formatted_timestamp


def calendar_days_since_submission(date_string):
    # Calculates calendar days since submission. Returns -1 if the date string is invalid

    formatted_timestamp = strip_date_string(date_string)
    if formatted_timestamp == "":
        return -1

    try:
        diff = (datetime.datetime.now().date() - datetime.datetime.strptime(formatted_timestamp, '%Y %d %b %H:%M').date()).days
    except Exception as e:
        log("Error", f"Could not calculate days since submission. Date string: {date_string}")
        diff = -1

    return diff


def hours_since_submission(date_string):
    # Calculates hours since submission. Returns -1 if the date string is invalid

    formatted_timestamp = strip_date_string(date_string)
    if formatted_timestamp == "":
        return -1

    # Calculate the time difference between now and the submitted timestamp
    try:
        time_difference = datetime.datetime.now() - datetime.datetime.strptime(formatted_timestamp, "%Y %d %b %H:%M")
    except Exception as e:
        log("Error", f"Could not calculate hours since submission. Date string: {date_string}")
        return -1

    # Calculate the total hours difference
    return (time_difference.total_seconds() / 3600)


def get_dashboard_assignments():
    global driver, TIMEOUT

    assignment_urls = [] # URLs of each assignment
    assm_num = [] # How many of each assignment there are
    
    # Get how many of each assignment there are
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[contains(concat(' ', @class, ' '), ' todo-badge ')]/span")))
    for e in driver.find_elements(By.XPATH, "//div[contains(concat(' ', @class, ' '), ' todo-badge ')]/span"):
        t = e.get_attribute("innerText") # Gets text of both span
        assm_num.append(int(t[0])) # Add to int
    del assm_num[1::2] # Remove invalid items

    # Get assignment URL
    for e in driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' todo ')]//a"):
        assignment_urls.append(e.get_attribute("href"))

    return assignment_urls, assm_num


def wait_for_load():
    # Attempts to get the submission date from an assignment. Waits up to TIMEOUT
    global TIMEOUT

    date_string = ""

    # Keep trying to get the date for a specified duration of time
    wait_counter = 0
    while wait_counter < TIMEOUT:
        try:
            # Wait until the document loads, then select the most recent assignment
            dropdown = Select(driver.find_element(By.ID, 'submission_to_view'))
            date_string = dropdown.first_selected_option.text
        except:
            # If the element is not found, check for multiple submissions
            element = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//*[@id='multiple_submissions']")))
            date_string = element.get_attribute("innerText") # Gets assignment date

        # If neither are found, keep trying for a few seconds
        if date_string:
            break
        else:
            wait_counter += 1
            time.sleep(1)

    return date_string


def check_assignment(tutor_name, current_tutor):
    global driver, tutors

    date_string = wait_for_load()
    if date_string:

        is_overdue = False
        hours = hours_since_submission(date_string)
        days = calendar_days_since_submission(date_string)

        if hours >= 0 and days >= 0:
            # Check if assignment is overdue if all params are valid
            if USE_HOURS:
                is_overdue = hours > OVERDUE_LENGTH
            else:
                is_overdue = days > OVERDUE_LENGTH

            if is_overdue:
                # Take a screenshot if overdue
                time.sleep(2)
                is_overdue = True
                screenshot(tutor_name, tutors[current_tutor].get_overdue() + 1)

            tutors[current_tutor].add_assignment(hours, days, is_overdue)        
    else:
        log(tutor_name, "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (driver.title))



configure_outputs()
log("Wolsey Hall Oxford", "Dashboard Checker - Version %s" % (VERSION))

if True:
    # Create chrome driver instance
    Driver = driver.Driver(options_array, TIMEOUT)

    # Log in as admin user
    login(driver, "account.txt")
    userIDs, tutor_names = load_tutors("tutors.json")

    # Array of tutor classes to store data
    tutors = []
    for i in range(0, len(userIDs)):
        tutors.append(Tutor(tutor_names[i], userIDs[i]))

    # Loop through each user in the JSON file, log in as each one
    for current_tutor in range(0,len(userIDs)):
        if act_as_user(userIDs[current_tutor], tutor_names[current_tutor]):
            
            # Wait for the dashboard to fully load
            WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CLASS_NAME, "events_list.coming_up")))

            # Check Dashboard, find assignments due to mark
            if "todo-list-header" not in driver.page_source:
                output(tutor_names[current_tutor], "No Items on dashboard")
            else:
                # Check if there are more assignments to load
                for more_link in driver.find_elements(By.XPATH, "//ul//li//a[contains(concat(' ', @class, ' '), ' more_link ')]"):
                    t = more_link.get_attribute("innerText")
                    if "more..." in t:
                        more_button = driver.find_element(By.XPATH, "//a[contains(text(), 'more..')]")
                        more_button.click()

                assignment_urls, assm_num = get_dashboard_assignments()
                
                # Start iterating through each assignment
                for current_assignment in range(0, len(assignment_urls)):

                    try:
                        # Try to load each assignment, wait for timeout
                        driver.get(assignment_urls[current_assignment])
                        if wait_for_load() == "":
                            log(tutor_names[current_tutor], "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (driver.title))
                            continue

                        if assm_num[current_assignment] == 1:
                            # If there is only one submission for the assignment, check it and continue
                            check_assignment(tutor_names[current_tutor], current_tutor)
                        else:
                            # Handle multiple submissions for the same assignment by opening dropdown, checking for multiple submissions
                            multiple_dropdown = driver.find_element(By.XPATH, "//i[contains(concat(' ', @class, ' '), ' icon-mini-arrow-down ')]")
                            multiple_dropdown.click()
                            time.sleep(1.5)

                            unmarked_assignments = driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' not_graded ')]")
                            
                            # Get the name of the current student
                            current_student_name_span = driver.find_element(By.XPATH, "//span[contains(concat(' ', @class, ' '), ' ui-selectmenu-status ')]")
                            current_student_name = current_student_name_span.find_element(By.CLASS_NAME, "ui-selectmenu-item-header").get_attribute("innerText")

                            students = []
                            for assignment in unmarked_assignments:

                                # Reload these again as the elements may have became stale
                                unmarked_assignments = driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' not_graded ')]")
                                student_name = assignment.find_element(By.CLASS_NAME, "ui-selectmenu-item-header").get_attribute("innerText")
                                student_click = assignment.find_element(By.CLASS_NAME, "ui-selectmenu-item-header")

                                if student_name in students:
                                    continue
                                students.append(student_name)
                                
                                # Only wait if the assignment we are checking does not require a re-load
                                if student_name != current_student_name:
                                    assignment.click()
                                    if wait_for_load() == "":
                                        log(tutor_names[current_tutor], "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (driver.title))
                                        continue
                                
                                check_assignment(tutor_names[current_tutor], current_tutor)

                                # Re-click the dropdown if the page requires a re-load
                                if student_name != current_student_name:
                                    multiple_dropdown = driver.find_element(By.XPATH, "//i[contains(concat(' ', @class, ' '), ' icon-mini-arrow-down ')]")
                                    multiple_dropdown.click()
                                    time.sleep(1.5)                    

                    except Exception as e:
                        log(tutor_names[current_tutor], f"Error checking assignment")
                    

                output(tutor_names[current_tutor], f"Assignments overdue: {tutors[current_tutor].get_overdue()}")

            # Stop acting as user
            try:
                # We put this in a try catch, as if the user tries to stop acting as themselves, the button does not exist
                stop_button = driver.find_element(By.LINK_TEXT, "Stop acting as user")
                stop_button.click()
                time.sleep(0.5)
            except:
                pass


#except Exception as e:
 #  log("Error", e)


log("Status", "Application exited cleanly")
