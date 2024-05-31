# This file contains all functionality completed by the chrome driver

from selenium import webdriver

class Driver:

    # Constructor. Initialises chrome driver
    def __init__(self, options_array, timeout):
        self.TIMEOUT = timeout

        # Convert options array to chrome options, and initialise driver
        options = webdriver.ChromeOptions()
        for i in options_array:
            options.add_argument(i)

        try:
            self.driver = webdriver.Chrome(service = Service(), options=chrome_options)
        except Exception as e:
            print("Fatal Error: Could not initialise chrome driver. Message: " + str(e))
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
        self.driver.get(CANVAS_URL + "/login/canvas")

        # Wait for elements to be present
        username_box = WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.ID, "pseudonym_session_unique_id")))
        pass_box = WebDriverWait(self.driver, self.TIMEOUT).until(EC.presence_of_element_located((By.ID, "pseudonym_session_password")))
        login_button = WebDriverWait(self.driver, self.TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Log In']")))

        # Fill in the login form    
        username_box.send_keys(username)
        pass_box.send_keys(password)
        login_button.click()

        # Check that login was successful
        if driver.title == "Dashboard":
            log("Authentication Complete", "Logged in as %s" % (username))
        else:
            log("Fatal Error", "Could not log in - Username or password incorrect, or browser timed out.")
            sys.exit()

        