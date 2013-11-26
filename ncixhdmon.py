from bs4 import BeautifulSoup
import urllib.request, urllib.parse, urllib.error
import re
from operator import itemgetter
import datetime

f = urllib.request.urlopen("http://www.ncix.com/products/?minorcatid=109&po=0&ps=2")
data = f.read()

soup = BeautifulSoup(data)
span = soup.findAll(name = "span", attrs = {"class" : "listing"})

products = {}

widestPrice = 0
widestCap = 0

for s in span:
	link = s.find('a').string
	node = s

	# Find the first tr parent
	while node.name != 'tr':
		node = node.parent

	priceText = node.find('strong').findAll(text=re.compile('\$([0-9]+,)?[0-9]+\.[0-9]+'))[0]
	priceText = priceText.strip().strip('$').replace(',','')

	if len(priceText) > 0:
		price = float(priceText)
		products[link] = price


for p in products:
	matchTB = re.search("([0-9.]+)\s?TB", p)
	matchGB = re.search("([0-9.]+)\s?GB", p)
	if matchTB:
		cap = float(matchTB.group(1)) * 1000
	elif matchGB:
		cap = float(matchGB.group(1))
	else:
		print("Warning: capacity not found for " + p)
		cap = -1

	price = products[p]
	ratio = price / cap
	products[p] = (price, cap, ratio)

now = datetime.datetime.now()
print("Generated on " + str(now))
print("Prix\tTaille\t$/GB\tNom")
print("---------------------------")

products = [p for p in list(products.items()) if p[1][2] > 0]

def sortkey(element):
	return element[1][2]

for i in sorted(products, key=sortkey):
	if i[1][1] > 0:
		if i[1][1] >= 1000:
			cap = "%.1f TB" % (i[1][1] / 1000)
		else:
			cap = "%d GB" % i[1][1]
		print("%.2f\t%s\t%.3f\t" % (i[1][0], cap, i[1][2]) + i[0])
