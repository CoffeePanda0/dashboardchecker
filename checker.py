# Description: This file contains the Checker class, which is responsible for all browser interactions

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

# Custom modules
from utils import *



# Removes trailing words and characters from canvas date string
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


# Calculates calendar days since submission. Returns -1 if the date string is invalid
def calendar_days_since_submission(date_string):
    formatted_timestamp = strip_date_string(date_string)
    if formatted_timestamp == "":
        return -1

    try:
        diff = (datetime.datetime.now().date() - datetime.datetime.strptime(formatted_timestamp, '%Y %d %b %H:%M').date()).days
    except Exception as e:
        log("Error", f"Could not calculate days since submission. Date string: {date_string}")
        diff = -1

    return diff


# Calculates hours since submission. Returns -1 if the date string is invalid
def hours_since_submission(date_string):
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


class Checker:

    # Constructor. Initialises chrome driver
    def __init__(self, options_array, timeout, canvas_url, use_hours, overdue_length):
        self.TIMEOUT = timeout
        self.CANVAS_URL = canvas_url
        self.USE_HOURS = use_hours
        self.OVERDUE_LENGTH = overdue_length

        # Convert options array to chrome options, and initialise driver
        options = webdriver.ChromeOptions()
        for i in options_array:
            options.add_argument(i)

        try:
            self.driver = webdriver.Chrome(service = Service(), options=options)
        except Exception as e:
            log("Fatal Error", "Could not initialise chrome driver. Message: " + str(e))
            sys.exit()


    # Function to log in to canvas using credential file
    def login(self, account_file_name):
        try:
            with open(account_file_name, "r") as f:
                lines = f.readlines()
                username = lines[0].strip() 
                password = lines[1].strip()
        except FileNotFoundError:
            log("Fatal error", "Could not log in - The account.txt file could not be loaded")
            sys.exit()
        except IndexError:
            log("Fatal error", "Could not log in - Username or password not found in account file")
            sys.exit()

        # Log in to canvas given the provided credentials
        self.driver.get(self.CANVAS_URL + "/login/canvas")

        # Wait for elements to be present
        username_box = WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.ID, "pseudonym_session_unique_id")))
        pass_box = WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.ID, "pseudonym_session_password")))
        login_button = WebDriverWait(self.driver, self.TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Log In']")))

        # Fill in the login form    
        username_box.send_keys(username)
        pass_box.send_keys(password)
        login_button.click()

        # Check that login was successful
        if self.driver.title == "Dashboard":
            log("Authentication Complete", "Logged in as %s" % (username))
        else:
            log("Fatal Error", "Could not log in - Username or password incorrect, or browser timed out.")
            sys.exit()


    # Act as a user given their ID. Return True if successful, False otherwise
    def act_as_user(self, user_id, user_name):
        self.driver.get(self.CANVAS_URL + f"/users/{user_id}/masquerade")
        try:
            WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.LINK_TEXT, "Proceed")))
            proceed_button = self.driver.find_element(By.LINK_TEXT, "Proceed")
            proceed_button.click()
        except:
            log("Act as user - Error", f"You do not have permission to act as {user_name}")
            return False
        
        if self.driver.title == "Dashboard":
            log("Act as user - Success", f"Acting as user {user_name}")
            return True
        else:
            log("Act as user - Error", f"Could not act as user {user_name}")
            return False
    

    # Get the dashboard assignments. Returns URLs of all assignments, and an list of how many of each assignment are behind each URL.
    def get_dashboard_assignments(self):
        # Check if there are more assignments to load
        for more_link in self.driver.find_elements(By.XPATH, "//ul//li//a[contains(concat(' ', @class, ' '), ' more_link ')]"):
            t = more_link.get_attribute("innerText")
            if "more..." in t:
                more_button = self.driver.find_element(By.XPATH, "//a[contains(text(), 'more..')]")
                more_button.click()

        assignment_urls = [] # URLs of each assignment
        assm_num = [] # How many of each assignment there are
        
        # Get how many of each assignment there are
        WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[contains(concat(' ', @class, ' '), ' todo-badge ')]/span")))
        for e in self.driver.find_elements(By.XPATH, "//div[contains(concat(' ', @class, ' '), ' todo-badge ')]/span"):
            t = e.get_attribute("innerText") # Gets text of both span
            assm_num.append(int(t[0])) # Add to int
        del assm_num[1::2] # Remove invalid items

        # Get assignment URL
        for e in self.driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' todo ')]//a"):
            assignment_urls.append(e.get_attribute("href"))

        return assignment_urls, assm_num
    

    # Waits until the dashboard has loaded. Returns true if dashboard has unmarked assignments, false if empty
    def dashboard_has_assignments(self):
        # Wait for the dashboard to fully load
        WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.CLASS_NAME, "events_list.coming_up")))

        # Check Dashboard, find assignments due to mark
        return "todo-list-header" in self.driver.page_source


    # Waits up until TIMEOUT to get the submission date from an assignment.
    def wait_for_submission(self): 
        date_string = ""

        # Keep trying to get the date for a specified duration of time
        wait_counter = 0
        while wait_counter < self.TIMEOUT:
            try:
                # Wait until the document loads, then select the most recent assignment
                dropdown = Select(self.driver.find_element(By.ID, 'submission_to_view'))
                date_string = dropdown.first_selected_option.text
            except:
                # If the element is not found, check for multiple submissions
                element = WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//*[@id='multiple_submissions']")))
                date_string = element.get_attribute("innerText") # Gets assignment date

            # If neither are found, keep trying for a few seconds
            if date_string:
                break
            else:
                wait_counter += 1
                time.sleep(1)

        return date_string
    

    # Stops acting as a user
    def stop_acting_as_user(self):
        try:
            # We put this in a try catch, as if the user tries to stop acting as themselves, the button does not exist
            stop_button = self.driver.find_element(By.LINK_TEXT, "Stop acting as user")
            stop_button.click()
            time.sleep(0.5)
        except:
            pass


    # Checks if a loaded assignment is overdue
    def check_assignment_overdue(self, tutor_name, tutors_list, current_tutor):
        date_string = self.wait_for_submission()
        if date_string:

            is_overdue = False
            hours = hours_since_submission(date_string)
            days = calendar_days_since_submission(date_string)

            if hours >= 0 and days >= 0:
                # Check if assignment is overdue if all params are valid
                if self.USE_HOURS:
                    is_overdue = hours > self.OVERDUE_LENGTH
                else:
                    is_overdue = days > self.OVERDUE_LENGTH

                if is_overdue:
                    # Take a screenshot if overdue
                    time.sleep(2)
                    is_overdue = True
                    screenshot(self, tutor_name, tutors_list[current_tutor].get_overdue() + 1)

                tutors_list[current_tutor].add_assignment(hours, days, is_overdue)        
        else:
            log(tutor_name, "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (self.driver.title))


    # Checks through a list of assignments
    def check_assignments(self, assignment_urls, submission_count, tutor_name, tutors_list, current_tutor):
        # Start iterating through each assignment
        for current_assignment in range(0, len(assignment_urls)):

            try:
                # Try to load each assignment, wait for timeout
                self.driver.get(assignment_urls[current_assignment])
                if self.wait_for_submission() == "":
                    log(tutor_name, "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (self.driver.title))
                    continue

                if submission_count[current_assignment] == 1:
                    # If there is only one submission for the assignment, check it and continue
                    self.check_assignment_overdue(tutor_name, tutors_list, current_tutor)
                else:
                    # Handle multiple submissions for the same assignment by opening dropdown, checking for multiple submissions
                    multiple_dropdown = self.driver.find_element(By.XPATH, "//i[contains(concat(' ', @class, ' '), ' icon-mini-arrow-down ')]")
                    multiple_dropdown.click()
                    time.sleep(1.5)

                    unmarked_assignments = self.driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' not_graded ')]")
                    
                    # Get the name of the current student
                    current_student_name_span = self.driver.find_element(By.XPATH, "//span[contains(concat(' ', @class, ' '), ' ui-selectmenu-status ')]")
                    current_student_name = current_student_name_span.find_element(By.CLASS_NAME, "ui-selectmenu-item-header").get_attribute("innerText")

                    students = []
                    # Iterate through each student in the dropdown
                    for assignment in unmarked_assignments:

                        # Reload these again as the elements may have became stale
                        unmarked_assignments = self.driver.find_elements(By.XPATH, "//li[contains(concat(' ', @class, ' '), ' not_graded ')]")
                        student_name = assignment.find_element(By.CLASS_NAME, "ui-selectmenu-item-header").get_attribute("innerText")

                        # Make sure we haven't already checked this submission
                        if student_name in students:
                            continue
                        students.append(student_name)
                        
                        # Only wait if the assignment we are checking does not require a re-load
                        if student_name != current_student_name:
                            assignment.click()
                            if self.wait_for_submission() == "":
                                log(tutor_name, "COULD NOT CHECK ASSIGNMENT (Timed out waiting for page to load): %s" % (self.driver.title))
                                continue
                        
                        self.check_assignment_overdue(tutor_name, tutors_list, current_tutor)

                        # Re-click the dropdown if the page requires a re-load
                        if student_name != current_student_name:
                            multiple_dropdown = self.driver.find_element(By.XPATH, "//i[contains(concat(' ', @class, ' '), ' icon-mini-arrow-down ')]")
                            multiple_dropdown.click()
                            time.sleep(1.5)                    

            except Exception as e:
                log(tutor_name, f"Error checking assignment: " + str(e))
        