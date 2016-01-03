from bs4 import BeautifulSoup
import re
import datetime
import jinja2
import sys
import requests

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
        td {
            vertical-align: top;
        }
        td.iframe {
            width: 75%;
        }
        td.iframe span {
            display: inline-block;
            width: 80px;
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
        iframe {
            width: 100%;
            height: 600px;
            margin-top: 10px;
        }
    </style>
    <script src="http://ajax.googleapis.com/ajax/libs/jquery/2.0.3/jquery.min.js"></script>
    <script type="application/javascript">
        $(document).ready(function() {
            $('td.iframe a.shrink').hide();
            $('td.iframe a.expand').click(function(e) {
                e.preventDefault();
                $(this).hide();
                $(this).parent().find('a.shrink').show();
                $(this).parent().parent().after('<iframe src="' + $(this).attr('href') + '"></iframe>');
            });
            $('td.iframe a.shrink').click(function(e) {
                e.preventDefault();
                $(this).hide();
                $(this).parent().find('a.expand').show();
                $(this).closest('.iframe').find('iframe').remove();
            });
        });
    </script>
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
                    <td class="iframe"><div><span>[<a class="expand" href="{{ result.href }}">expand</a><a class="shrink" href="#">shrink</a>]</span><a href="{{ result.href }}">{{ result.name }}</a></div></td>
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
    f = requests.get('http://www.ncix.com/category/hard-drives-8a-109.htm')
    data = f.text

    soup = BeautifulSoup(data, "lxml")
    span = soup.findAll(name='span', attrs={'class': 'listing'})

    products = {}
    widestPrice = 0
    widestCap = 0

    # gather items
    for s in span:
        link_node = s.find('a')
        if not link_node:
            continue

        href = link_node['href']
        name = link_node.string
        node = s

        # find the first tr parent
        while node.name != 'tr':
            node = node.parent

        # Find the td of that tr containing the price
        td = node.find(name='td', attrs={'align': 'right'})

        # Find the price in the td
        priceText = td.find('strong').find(text=re.compile(r'\$([0-9]+,)?[0-9]+\.[0-9]+'))

        # Cleanup the price string
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
    templates = {
        'text': template_plaintext,
        'plain': template_plaintext,
        'html': template_html
    }
    template = templates['text']

    # get template
    if len(sys.argv) > 1:
        if sys.argv[1] in templates:
            template = templates[sys.argv[1]]

    # get limit
    limit = sys.maxsize
    if len(sys.argv) > 2:
        limit = float(sys.argv[2])

    # get and output results
    results, warning_msgs = get_results(limit)
    print(output_results(results, warning_msgs, template))
