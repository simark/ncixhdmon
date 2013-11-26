from bs4 import BeautifulSoup
import urllib.request
import re
import datetime
import jinja2
import sys

# some templates
template_html = """<!doctype>
<html>
<head>
    <meta charset="utf-8">
    <title>ncixhdmon report</title>
    <style type="text/css">
        * {
            margin: 0;
        }
        body {
            margin: 25px;
            font-size: 16px;
            font-family: 'Ubuntu', 'Arial', 'Helvetica', sans-serif;
        }
        h1 {
            font-size: 150%;
            color: #444;
        }
        h3 {
            font-size: 110%;
            color: #666;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #ddd;
            padding: 15px;
        }
        td, th {
            padding: 10px;
            border: 1px solid #bbb;
        }
        tr:hover td {
            background: #eee;
        }
        th {
            background: #ddd;
        }
        h1, h3 {
            margin-bottom: 15px;
        }
        a:link, a:visited {
            text-decoration: none;
            color: #4892D6;
        }
        a:hover {
            text-decoration: underline;
        }

    </style>
</head>
<body>
    <h1>ncixhdmon report</h1>
    <h3>Generated on {{ gen_date }}</h3>
    <table>
        <thead>
            <tr>
                <th>Price ($)</th>
                <th>Capacity</th>
                <th>Ratio ($/GB)</th>
                <th>Name</th>
            </tr>
        </thead>
        <tbody>
            {% for result in results %}
                <tr>
                    <td>{{ result.price | round(2) }}</td>
                    <td>{{ result.cap_text }}</td>
                    <td>{{ result.ratio | round(3) }}</td>
                    <td><a href="{{ result.href }}">{{ result.name }}</a></td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>"""

template_plaintext = """     Price       Cap      $/GB  Name
==============================================================================
{% for result in results %}{{ '%10.2f' | format(result.price) }}{{ '%10s' | format(result.cap_text) }}{{ '%10.3f' | format(result.ratio) }}  {{ result.name }}
{% endfor %}"""


def format_cap(cap):
    if cap >= 1000:
        return '{:.1f}'.format(cap / 1000).rstrip('0').rstrip('.') + ' TB'
    else:
        return '{}'.format(cap).rstrip('0').rstrip('.') + ' GB'


def get_results():
    f = urllib.request.urlopen('http://www.ncix.com/products/?minorcatid=109&po=0&ps=2')
    data = f.read()

    soup = BeautifulSoup(data)
    span = soup.findAll(name='span', attrs={'class': 'listing'})

    products = []
    widestPrice = 0
    widestCap = 0

    # gather items
    for s in span:
        link_node = s.find('a')
        href = link_node['href']
        name = link_node.string
        node = s

        # find the first tr parent
        while node.name != 'tr':
            node = node.parent

        priceText = node.find('strong').findAll(text=re.compile('\$([0-9]+,)?[0-9]+\.[0-9]+'))[0]
        priceText = priceText.strip().strip('$').replace(',', '')

        if len(priceText) > 0:
            price = float(priceText)
            products.append({
                'href': 'http://www.ncix.com' + href,
                'name': name,
                'price': price
            })

    # format results
    results = []
    warning_msgs = []
    for p in products:
        name = p['name']
        price = p['price']

        matchTB = re.search('([0-9.]+)\s?TB', name)
        matchGB = re.search('([0-9.]+)\s?GB', name)
        if matchTB:
            cap = float(matchTB.group(1)) * 1000
        elif matchGB:
            cap = float(matchGB.group(1))
        else:
            warning_msgs.append('Warning: capacity not found for "{}"'.format(name))
            cap = -1

        ratio = price / cap
        if ratio > 0:
            results.append({
                'price': price,
                'cap': cap,
                'cap_text': format_cap(cap),
                'ratio': ratio,
                'href': p['href'],
                'name': name
            })

    # sort results by ratio
    sorted_results = sorted(results, key=lambda elem: elem['ratio'])

    return sorted_results, warning_msgs


def output_results(results, warning_msgs, template_str):
    env = jinja2.Environment()
    template = env.from_string(source=template_str)

    return template.render(gen_date=datetime.date.today(), results=results)


if __name__ == '__main__':
    template = template_plaintext
    if len(sys.argv) > 1:
        if sys.argv[1] == 'html':
            template = template_html
    results, warning_msgs = get_results()
    print(output_results(results, warning_msgs, template))
