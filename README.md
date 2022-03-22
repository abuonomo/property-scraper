# property-scraper

scrape property data.  
Use [poetry](https://python-poetry.org/) to set up environment.   
  
Activate virtualenv with poetry: `poetry shell`.   
Then, run commands from Makefile with venv activated: `make help`.   
```
all                 Run full pipeline 
codes               Get unit codes 
condense            Combine found data and get most important information 
transactions        Get transactions for units (run iteratively until complete all) 
update-chromedriver Download and unzip the chromedriver for your version 
```