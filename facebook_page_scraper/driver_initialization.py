#!/usr/bin/env python3

from seleniumwire import webdriver as seleniumWireWebDriver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import logging
import os

logger = logging.getLogger(__name__)
format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(format)
logger.addHandler(ch)


class Initializer:

    def __init__(self, browser_name, proxy=None, headless=True, devTools=False):
        self.browser_name = browser_name
        self.proxy = proxy
        self.headless = headless
        self.devTools = devTools

    def set_properties(self, browser_option):
        """adds capabilities to the driver"""
        if self.headless:
            browser_option.add_argument(
                '--headless')  # runs browser in headless mode
        else:
            if self.devTools:
                browser_option.add_argument("-devtools")
        browser_option.add_argument('--no-sandbox')
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument('--ignore-certificate-errors')
        browser_option.add_argument('--disable-gpu')
        browser_option.add_argument('--log-level=3')
        browser_option.add_argument('--disable-notifications')
        browser_option.add_argument('--disable-popup-blocking')
        return browser_option

    def set_driver_for_browser(self, browser_name, driver_install_config=None, remoteBrowser=None):
        """expects browser name and returns a driver instance"""
        if driver_install_config is None:
            driver_install_config = {}
        logger.setLevel(logging.INFO)
        # if browser is suppose to be chrome
        if browser_name.lower() == "chrome":
            browser_option = ChromeOptions()
            # automatically installs chromedriver and initialize it and returns the instance
            if self.proxy is not None:
                options = {
                    'https': 'https://{}'.format(self.proxy.replace(" ", "")),
                    'http': 'http://{}'.format(self.proxy.replace(" ", "")),
                    'no_proxy': 'localhost, 127.0.0.1'
                }
                logger.info("Using: {}".format(self.proxy))
                return seleniumWireWebDriver.Chrome(executable_path=ChromeDriverManager().install(),
                                        options=self.set_properties(browser_option), seleniumwire_options=options)

            if remoteBrowser is not None:
                selenium_grid_url = os.getenv('SELENIUM_GRID_URL') or driver_install_config.get('selenium_grid_url')
                if not selenium_grid_url:
                    raise Exception("SELENIUM_GRID_URL environment variable not set")

                # Use RemoteWebDriver with Firefox capabilities
                return webdriver.Remote(command_executor=selenium_grid_url, options=self.set_properties(browser_option))
            else:
                return seleniumWireWebDriver.Chrome(executable_path=ChromeDriverManager().install(), options=self.set_properties(browser_option))
        elif browser_name.lower() == "firefox":
            browser_option = FirefoxOptions()
            # Check if remoteBrowser is enabled (True) - use RemoteWebDriver
            if remoteBrowser is True:
                # Get the Selenium Grid URL from environment variable
                selenium_grid_url = os.getenv('SELENIUM_GRID_URL') or driver_install_config.get('selenium_grid_url')
                if not selenium_grid_url:
                    raise Exception("SELENIUM_GRID_URL environment variable not set")
                
                # Use RemoteWebDriver with Firefox capabilities
                return webdriver.Remote(command_executor=selenium_grid_url, options=self.set_properties(browser_option))
            else:
                # automatically installs geckodriver and initialize it and returns the instance
                return seleniumWireWebDriver.Firefox(executable_path=GeckoDriverManager(**driver_install_config).install(), options=self.set_properties(browser_option))
        else:
            # if browser_name is not chrome neither firefox than raise an exception
            raise Exception("Browser not supported!")

    def init(self, driver_install_config, remoteBrowser=None):
        """returns driver instance"""
        driver = self.set_driver_for_browser(self.browser_name, driver_install_config=driver_install_config, remoteBrowser=remoteBrowser)
        if driver is not None:
            driver.set_page_load_timeout(120)
        return driver
