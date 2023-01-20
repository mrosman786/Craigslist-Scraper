from scraper import Craigslist
  
scraper = Craigslist()

location_name= "new york"
category_name = "lessons & tutoring"

# scraping data
scraped_data = scraper.scrape(location_name, category_name)

# saving data to csv
output_format = "csv"
scraper.save_data(scraped_data, location_name, category_name, output_format)

# saving data to json

output_format = "json"
scraper.save_data(scraped_data, location_name, category_name, output_format)
