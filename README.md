# Craigslist Scraper

This script is used to scrape data from craigslist and can be used to gather information on a specific category of items. The user can then use the data gathered to perform analysis on the Title, Phone, Images Urls and other attributes of the items.

## Installation

To install the dependencies, run the following command:

```pip install -r requirements.txt```

## Usage

The script defines a `Craigslist` class, which has several methods to scrape different parts of the Craigslist website.
### Import Craigslist Class
```python
from scraper import Craigslist
cl = Craigslist()
```


### To scrape data 
```python
location_name = "abilene"
category_name = "pets"
scraped_data = cl.scrape(location_name, category_name)
```
if you leave `location_name` empty it will search for `whole USA`.



### To Save data
```python

output_format = "csv" 
cl.save_data(scraped_data, location_name, category_name, output_format)
```
It Supports two output formats `json` and `csv`.


## Note
Please note that this script is for educational and research purposes, and it is important to adhere to Craigslist's terms of service and refrain from scraping data without permission.


