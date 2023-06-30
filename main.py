import asyncio
import time
from datetime import datetime

import aiohttp
import csv
from dataclasses import dataclass, astuple

api_key_google = "your_api_google_key"


@dataclass
class Place:
    name: str
    address: str
    phone_number: str
    website: str
    rating: float


class PlaceGenerator:
    def __init__(self) -> None:
        self.location = None
        self.keyword = None

    async def _validate_location(self):
        location = input("Find location (city, village or ect): ")

        url = "http://api.geonames.org/searchJSON"
        params = {
            "q": location,
            "maxRows": 1,
            "username": "test_evgeniy"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

            if "geonames" in data and data["geonames"]:
                country = data['geonames'][0]['countryName']
                place = data['geonames'][0]['name']
                location = f"{country}: {place}"
                correct_location = input(f"Is {location} the correct location? (Y/N):")

            if correct_location in ("Y", "y") and country != place:
                return place
        print("Invalid location. Please enter a valid location.")
        return self._validate_location()

    def _validate_place(self):
        keyword = input("Find by keyword (cafe, restaurant or ect): ")
        if keyword:
            return keyword
        return self._validate_place()

    async def get_detail_page_api(self, id_list):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in id_list:
                url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={i}&key={api_key_google}"
                task = asyncio.ensure_future(self.fetch_place_details(session, url))
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            return [result for result in results if result]

    @staticmethod
    async def fetch_place_details(session, url) -> Place:
        async with session.get(url) as response:
            data = await response.json()
            if data['status'] == 'OK':
                place_details = data['result']
                name = place_details.get('name', None)
                address = place_details.get('formatted_address', None)
                phone_number = place_details.get('formatted_phone_number', None)
                website = place_details.get('website', None)
                rating = place_details.get('rating', 0.0)
                return Place(name=name, address=address, phone_number=phone_number, website=website, rating=rating)

    async def add_information_to_files(self, places):
        with open(f"{datetime.now()} - Place: {self.location} with keyword: {self.keyword}.csv", "w") as quotes:
            fields = ("name", "address", "phone_number", "website", "rating")
            writer = csv.writer(quotes)
            writer.writerow(fields)
            for pl in places:
                writer.writerow(astuple(pl))

    async def start(self):
        self.location = await self._validate_location()
        self.keyword = self._validate_place()

        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={self.location}&key={api_key_google}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

                radius = 5000

                lat = data["results"][0]['geometry']['location']['lat']
                lng = data["results"][0]['geometry']['location']['lng']

                bounds = data["results"][0].get("geometry", {}).get("viewport", {}).get("northeast", {})
                if bounds:
                    northeast_lat = bounds.get("lat")
                    northeast_lng = bounds.get("lng")
                    radius = max(abs(lat - northeast_lat), abs(lng - northeast_lng)) * 111000
        places = await self.start_search_place(f"{lat},{lng}", radius)

        new_list = []
        for place in places:
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            new_list += await self.start_search_near_place(f"{lat},{lng}", 1000)

        set_new = set(i["place_id"] for i in new_list + places)

        list_of_places = await self.get_detail_page_api(set_new)
        await self.add_information_to_files(list_of_places)

    async def start_search_place(self, location, radius):
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={self.keyword}&key={api_key_google}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                places = data['results']

            while "next_page_token" in data:
                next_page_token = data["next_page_token"]
                url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={self.keyword}&key={api_key_google}&pagetoken={next_page_token}"
                await asyncio.sleep(2)
                async with session.get(url) as response:
                    data = await response.json()
                    places += data['results']
        return places

    async def start_search_near_place(self, location, radius):
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={self.keyword}&key={api_key_google}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                places = data['results']
        return places


if __name__ == "__main__":
    start = time.time()
    bot = PlaceGenerator()
    asyncio.run(bot.start())
    end = time.time()

    print(end - start)


