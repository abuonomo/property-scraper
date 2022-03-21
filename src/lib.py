from selenium import webdriver
from pathlib import Path

class PropertyScraper:

    def __init__(self, driver_path: Path) -> None:
        self.driver_path = driver_path
        self.driver = webdriver.Chrome(executable_path=driver_path)
