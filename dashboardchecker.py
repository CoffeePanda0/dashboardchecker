# Credits - Alexander Thomas (CoffeePanda)
# This software is property of Wolsey Hall Oxford and is not to be distributed without permission

VERSION = "2.B" 

# Local module imports
import checker
from utils import *


# -- CONSTANTS --
CANVAS_URL = "https://wolseyhalloxford.instructure.com" # Canvas URL eg https://abc.infastructure.com
OVERDUE_LENGTH = 5 # How many either hours / days since submission until the assigmment is overdue
USE_HOURS = False # If True, uses hours since submission. If False, uses calendar days
TIMEOUT = 10 # How many seconds (maximum) to wait for a large assignment to load



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


# Application entry point
if __name__ == "__main__":

    configure_outputs()
    log("Wolsey Hall Oxford", "Dashboard Checker - Version %s" % (VERSION))

    if True:
        # Create chrome driver instance
        Driver = checker.Checker(options_array, TIMEOUT, CANVAS_URL, USE_HOURS, OVERDUE_LENGTH)

        # Log in as admin user
        Driver.login("account.txt")

        userIDs, tutor_names = load_json("tutors.json")
        # List of tutor classes to store data
        tutors = []
        for i in range(0, len(userIDs)):
            tutors.append(Tutor(tutor_names[i], userIDs[i]))

        # Loop through each user in the JSON file
        for current_tutor in range(0, len(userIDs)):
            # Try to masquerade as user
            if Driver.act_as_user(userIDs[current_tutor], tutor_names[current_tutor]):
                # Check Dashboard, find assignments due to mark
                if not Driver.dashboard_has_assignments():
                    output(tutor_names[current_tutor], "No Items on dashboard")
                else:
                    # Check all assignments on the dashboard
                    assignment_urls, submission_count = Driver.get_dashboard_assignments()
                    Driver.check_assignments(assignment_urls, submission_count, tutor_names[current_tutor], tutors, current_tutor) 

                    # Write number of overdue assignments to output file
                    output(tutor_names[current_tutor], f"Assignments overdue: {tutors[current_tutor].get_overdue()}")

                # Stop acting as user
                Driver.stop_acting_as_user()


    #except Exception as e:
    #  log("Error", e)


    log("Status", "Application exited cleanly")
