import contextlib
from bs4 import BeautifulSoup as Bs
import requests
from datetime import datetime
import urllib
import re
from retry import retry
import pandas as pd


class Craigslist:
    def __init__(self):
        # Regular expression to match US phone numbers
        self.phone_regex = r"[\+]?[\d]?[\s]?[(]?\d{3}[\s\-)]?[\s\.]?\d{3}[\s\-\.]?\d{4}"
        # headers to use in requests
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'If-Modified-Since': 'Sat, 24 Dec 2022 09:07:03 GMT',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

    @retry(tries=5, delay=5)
    def get_soup(self, url, soup=True, params=None):
        """
        Make a GET request to the specified URL
       :param url: the url to send the request to
       :param soup: return a BeautifulSoup object if True, otherwise return the raw response
       :param params: query parameters to include in the request
       :return: BeautifulSoup object or requests.Response object
       """

        if params is None:
            params = {}
        if params:
            response = requests.get(url, headers=self.headers, params=params)
        else:
            response = requests.get(url, headers=self.headers)

        return Bs(response.text, "lxml") if soup else response

    def _get_area_id(self, soup):
        """
        Get the area id from a soup object
        :param soup: BeautifulSoup object to extract the area id from
        :return: the area id
        """
        return str(soup).lower().split('areaid: "')[1].split('",')[0]

    def encode_query(self, query):
        """
        Encode a query string for use in a URL
        :param query: the query string to encode
        :return: the encoded query string
        """
        return urllib.parse.quote_plus(query)

    def search_category(self, label, area_id):
        """
        Search for a category by label and area ID
        :param label: the label of the category to search for
        :param area_id: the area ID to search in
        :return: the abbreviation of the category that matches the label, or None if no match is found
        """
        response = self.get_soup(
            f"https://sapi.craigslist.org/web/v7/categories/count?areaId={area_id}&cc=US&lang=en&query={self.encode_query(label)}",
            soup=False)
        json_data = response.json()

        for item in json_data.get("data").get("items"):
            if item.get("label") == label:
                return item.get("abbreviation")
            elif "items" in item:
                for sub_item in item.get("items"):
                    if sub_item.get("label") == label:
                        return sub_item.get("abbreviation")
                    elif "items" in sub_item:
                        for sub_sub_item in sub_item.get("items"):
                            if sub_sub_item.get("label") == label:
                                return sub_sub_item.get("abbreviation")
        return None

    def get_description(self, url):
        """
        Get the description of a specific listing
        :param url: the url of the listing to get the description of
        :return: the description of the listing
        """

        print(f"\t[+] Getting Description: {url}")
        soup = self.get_soup(url)
        if body := soup.find(id="postingbody"):
            with contextlib.suppress(Exception):
                body.find(class_="print-information print-qrcode-container").decompose()
            return body.get_text("\n", strip=True)
        return

    def extract_phone(self, desc_text):
        """
        Extract phone numbers from a description text
        :param desc_text:  to extract phone numbers
        :return:  phone number found in the description test
        """

        compiled = re.compile(self.phone_regex)
        if mo := compiled.search(desc_text):
            return mo.group()
        else:
            return

    def search_city(self, city_name):

        params = {
            'cc': 'US',
            'lang': 'en',
            'query': city_name,
        }
        resp = self.get_soup('https://sapi.craigslist.org/web/v7/suggest/location', params=params, soup=False)
        if items := resp.json().get("data").get("items"):
            item = items[0]
            return f'https://{item.get("url")}'
        else:
            print("[+] city not found.")
            return

    def _make_api(self, category_id, area_id):
        return f"https://sapi.craigslist.org/web/v7/postings/search/full?batch={area_id}-0-360-0-0&cc=US&lang=en&searchPath={category_id}"

    def get_all_locations(self, region="us"):
        sp = self.get_soup(f"https://geo.craigslist.org/iso/{region}")
        sites_ul = sp.find("ul", "geo-site-list")
        sites_list = sites_ul.findAll("a")
        return [
            {"site_name": site.get_text(strip=True), "site_url": site.get("href")}
            for site in sites_list
        ]

    def iter_listings(self, location_name, category_name, category_key, area):
        """
        Iterate over the listings of a specific category in a specific location
        :param location_name: the name of the location
        :param category_name: the name of the category
        :param category_key: the key of the category
        :param area: the area id
        :return: a data list
        """

        listings = []
        print(f"\n[+] Scraping:  {location_name} , category: {category_name}")
        url = self._make_api(category_key, area)
        response = self.get_soup(url, soup=False)
        jd = response.json()
        data = jd.get("data", {})
        total_results = data.get("totalResultCount")
        print(f"[+] Found: {total_results} results.")
        if total_results:
            decode = data['decode']
            locations = decode['locations']

            min_posting_id = decode['minPostingId']
            min_posted_date = decode['minPostedDate']

            for index, item in enumerate(data['items'][:total_results], start=1):
                title = item[-1]
                encoded_string = item[4]
                [details, *_] = encoded_string.split("~")
                [location_id, _, *_] = details.split(":")
                posted_date = datetime.fromtimestamp(min_posted_date + item[1])
                images = []
                if isinstance(item[-3], list):
                    image_slugs = item[-3][1:]

                    images = [
                        f'https://images.craigslist.org/{imageSlug.split(":")[1]}_300x300.jpg'
                        for imageSlug in image_slugs
                    ]

                posting_id = str(min_posting_id + item[0])

                loc_data = locations[int(location_id)]

                hostname = loc_data[1]
                sub_area_abbr = loc_data[2] if len(loc_data) == 3 else None

                if sub_area_abbr:
                    path = "/".join([sub_area_abbr, category_key, posting_id])
                else:
                    path = "/".join([category_key, posting_id])

                service_url = f'https://{hostname}.craigslist.org/{path}.html'

                description = self.get_description(service_url)
                phone = None
                if description:
                    phone = self.extract_phone(description)
                out_row = {
                    "location_name": location_name,
                    "category_name": category_name,
                    "posting_id": posting_id,
                    "posted_at": posted_date.strftime("%m/%d/%Y, %H:%M:%S"),
                    "service_url": service_url,
                    "title": title,
                    "phone": phone,
                    "images_urls": images,
                    "description": description}
                listings.append(out_row)
        return listings

    def scrape(self, location_name=None, category_name="lessons & tutoring"):
        listings = []
        # Search for listings in a specific location
        if location_name:
            if location_url := self.search_city(location_name):
                sp = self.get_soup(location_url)
                area = self._get_area_id(sp)

                if category_key := self.search_category(category_name, area_id=area):
                    listings = self.iter_listings(location_name, category_name, category_key, area)
                else:
                    print(f"[-] Category [{category_name}] not available in [{location_name}]")

        else:
            locations = self.get_all_locations()
            for location in locations:
                location_url = location.get("site_url")
                loc_name = location.get("site_name")
                sp = self.get_soup(location_url)
                area = self._get_area_id(sp)
                if category_key := self.search_category(
                        category_name, area_id=area
                ):
                    listings = self.iter_listings(loc_name, category_name, category_key, area)
                else:
                    print(f"[-] Category [{category_name}] not available in [{loc_name}]")
        return listings

    def save_data(self, data, location_name=None, category_name="lessons & tutoring", output_format="csv"):
        if data:
            df = pd.DataFrame(data)
            df.index += 1
        else:
            df = pd.DataFrame([{"location_name": "", "category_name": "", "posting_id": "", "posted_at": "",
                                "service_url": "", "title": "", "phone": "", "images_urls": "", "description": ""}])

        filename = f"{location_name or 'all'}_{category_name}.{output_format}".replace(" ", "")
        if output_format == "csv":
            df["images_urls"] = df["images_urls"].apply(lambda x: ", ".join(x))
            df.to_csv(filename)
        elif output_format == "json":
            df.to_json(filename, orient='records', indent=3)
        else:
            print("[-] Invalid output Format. Allowed csv/json.")
        print(f"\n[+] Data saved to: {filename}")
