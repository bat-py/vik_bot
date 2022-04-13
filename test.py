from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="vik_bot")

location = geolocator.reverse("41.376534, 69.350459")
location_list = location.address.split(', ')
location = ', '.join(location_list[:-2])
print(location)
#print(location.address)