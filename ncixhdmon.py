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
        h1, h3, div.warning {
            margin-bottom: 15px;
        }
        a:link, a:visited {
            text-decoration: none;
            color: #4892D6;
        }
        a:hover {
            text-decoration: underline;
        }
        div.warning {
            background: #F5E498;
            padding: 15px;
            border-radius: 2px;
            border: 1px solid #C2B478;
        }
        div.warning p {
            line-height: 150%;
            color: #222;
        }

    </style>
</head>
<body>
    <h1>ncixhdmon report</h1>
    <h3>Generated {{ gen_date }}</h3>
    {% if warning_msgs %}
        <div class="warning">
            {% for msg in warning_msgs %}
                <p>{{ msg }}</p>
            {% endfor %}
        </div>
    {% endif %}
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

template_plaintext = """     ncixhdmon report - generated {{ gen_date }}
{% if warning_msgs %}
{% for msg in warning_msgs %}** {{ msg }} **
{% endfor %}{% endif %}
     Price       Cap      $/GB  Name
==============================================================================
{% for result in results %}{{ '%10.2f' | format(result.price) }}{{ '%10s' | format(result.cap_text) }}{{ '%10.3f' | format(result.ratio) }}  {{ result.name }}
{% endfor %}"""


def format_cap(cap):
    if cap >= 1000:
        return '{:.1f}'.format(cap / 1000).rstrip('0').rstrip('.') + ' TB'
    else:
        return '{}'.format(cap).rstrip('0').rstrip('.') + ' GB'


def get_results(limit):
    f = urllib.request.urlopen('http://www.ncix.com/products/?minorcatid=109&po=0&ps=2')
    data = f.read()

    soup = BeautifulSoup(data)
    span = soup.findAll(name='span', attrs={'class': 'listing'})

    products = {}
    widestPrice = 0
    widestCap = 0

    # gather items
    for s in span:
        link_node = s.find('a')
        href = 'http://www.ncix.com' + link_node['href']
        name = link_node.string
        node = s

        # find the first tr parent
        while node.name != 'tr':
            node = node.parent

        priceText = node.find('strong').findAll(text=re.compile('\$([0-9]+,)?[0-9]+\.[0-9]+'))[0]
        priceText = priceText.strip().strip('$').replace(',', '')

        if len(priceText) > 0:
            price = float(priceText)
            products[href] = {
                'name': name,
                'price': price
            }

    # format results
    results = []
    warning_msgs = []
    for href, p in products.items():
        name = p['name']
        price = p['price']

        matchTB = re.search('([0-9.]+)\s?tb', name.lower())
        matchGB = re.search('([0-9.]+)\s?gb', name.lower())
        if matchTB:
            cap = float(matchTB.group(1)) * 1000
        elif matchGB:
            cap = float(matchGB.group(1))
        else:
            warning_msgs.append('Warning: capacity not found for "{}"'.format(name))
            cap = -1

        ratio = price / cap
        if ratio > 0 and cap <= limit:
            results.append({
                'price': price,
                'cap': cap,
                'cap_text': format_cap(cap),
                'ratio': ratio,
                'href': href,
                'name': name
            })

    # sort results by ratio
    sorted_results = sorted(results, key=lambda elem: elem['ratio'])

    return sorted_results, warning_msgs


def output_results(results, warning_msgs, template_str):
    env = jinja2.Environment()
    template = env.from_string(source=template_str)

    return template.render(gen_date=datetime.date.today(), results=results,
                           warning_msgs=warning_msgs)


if __name__ == '__main__':
    template = template_plaintext
    if len(sys.argv) > 1:
        if sys.argv[1] == 'html':
            template = template_html
    limit = sys.maxsize
    if len(sys.argv) > 2:
        limit = float(sys.argv[2])
    results, warning_msgs = get_results(limit)
    print(output_results(results, warning_msgs, template))
