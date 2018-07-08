import scrapy
from scrapy_splash import SplashRequest
import re
from datetime import timedelta
import json
from scrapy.http.headers import Headers
import sys

class SearchSpyder(scrapy.Spider):
    name = 'search'
    start_urls = [
        'https://www.realestate.co.jp/rent/listing?prefecture=JP-13&max_price=200000&min_meter=40&pets=1'
    ]

    def __init__(self, filename=None, **kwargs):
        super(SearchSpyder, self).__init__()
        self.apartments = []
        self.move_in_fees = []
        self.rents = []
        self.rents.append([
                u'url',
                u'Monthly Rent (MR)',
                u'Move-In Fees (MIF)',
                u'MIF - MR',
                u'Deposit',
                u'Key Money',
                u'Agency Fee',
                u'Guarantor Fee',
                u'Lock Exchange Fee',
                u'Fire Insurance',
                u'Other',
                u'Size',
                u'Location',
                u'Time to office',
                u'Commute cost',
                u'Directions'
        ])
        self.arrive_at_9am_only_trains = u'data=!3m1!4b1!4m16!4m15!1m5!1m1!1s0x6018edbd99a623d5:0x2c93d677cfb8b16d!2m2!1d139.6369342!2d35.7268406!1m0!2m6!5e1!5e2!5e3!6e1!7e2!8j1531213200!3e3'
        self.arrive_at_9am = u'data=!4m6!4m5!2m3!6e1!7e2!8j1531213200!3e3'
        self.total_move_in_fees = 0.0
        self.total_rent = 0.0
        self.count = 0
        #self.directions = u'https://www.google.com/maps/dir/?api=1&travelmode=transit&destination=35.6619147,139.7361128&origin='
        self.directions1 = u'https://www.google.com/maps/dir/'
        self.directions2 = u'/35.6619147,139.7361128/@35.7008346,139.5592397,11z/' + self.arrive_at_9am
        self.time_pattern = '(?:(\d+) h)?(?: )?(?:(\d+) m)?'
        self.matcher = re.compile(self.time_pattern)


    def parse(self, response):
        if response.status == 200:
            try:
                viewLinks = response.css("body.lang-en div#top.container div.row div.col-md-8 div.rej-property-list div.property-listing").xpath("//div[contains(@class, 'listing-body')]/div[contains(@class, 'listing-left-col')]/a/@href").extract()
                dedupViewLinks = list(set(viewLinks))

                # follow rent view
                for viewLink in dedupViewLinks :
                    if viewLink is not None:
                        viewUrl = response.urljoin(viewLink)
                        yield scrapy.Request(viewUrl, callback=self.parse_view)

                paginator = response.css('body.lang-en div#top.container div.row ul.paginator li.pagination-next')

                if len(paginator) > 0:
                    # follow next page
                    for next in paginator[0].css('a::attr(href)'):
                        yield response.follow(next, self.parse)
            except:
                print("Unexpected error list:", sys.exc_info()[0])
                raise
        else:
            print('Not ok request list:{}'.format(response.status))

    def parse_view(self, response):
        if response.status == 200:
            try:
                unitAtts = {}
                unitAtts['url'] = response.url

                # Details
                detailsTable = response.xpath('/html/body/div[3]/div[2]/div[1]/div/div[3]/div[1]/dl')
                detailNames = detailsTable.css('dt::text').extract()
                detailValues = detailsTable.css('dd::text').extract()

                for index in range(len(detailNames)):
                    unitAtts[detailNames[index].strip()] = detailValues[index].strip()

                # Rent & Fees
                feesTable = response.xpath('/html/body/div[3]/div[2]/div[1]/div/div[3]/div[3]/div[2]/dl')
                feesNames = feesTable.css('dt::text').extract()
                feesValues = feesTable.css('dd::text').extract()

                for index in range(len(feesNames)):
                    unitAtts[feesNames[index].encode('ascii', 'ignore').strip().encode('utf-8')] = feesValues[index].encode('ascii', 'ignore').strip().lstrip(u'\xa5').replace(',','').encode('utf-8')
                    

                # Directions
                gmap = response.css('div.js-rej-map')
                lat = gmap.css("::attr('data-lat')").extract_first()
                lng = gmap.css("::attr('data-lng')").extract_first()
                address = (gmap.css("::attr('data-address')").extract_first() or '').encode('utf-8')

                directions1 = self.directions1.encode('utf-8')
                directions2 = self.directions2.encode('utf-8')
                directions = u''

                if lat == '' or lng == '' or float(lat) == 0.0  or float(lng) == 0.0:
                    directions = directions1 + address + directions2
                else:
                    directions = directions1 + lat + ',' + lng + directions2

                unitAtts['directions'] = directions
                callbackFn = self.parse_map(unitAtts)

                RENDER_HTML_URL = 'http://localhost:8050/render.html'
                body = json.dumps({'url': directions, 'wait': 2}, sort_keys=True)
                headers = Headers({'Content-Type': 'application/json',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en',
                    'Referer': response.url,
                    'User-Agent': 'Scrapy/1.5.0 (+https://scrapy.org)'
                })

                yield scrapy.Request(RENDER_HTML_URL, callback=callbackFn, method="POST", body=body, headers=headers)
            except:
                print("Unexpected error view:", sys.exc_info()[0])
                raise
        else:
            print('Not ok request view:{}'.format(response.status))

    def parse_map(self, unitAtts):
        def toTimedelta(item):
            result = self.matcher.match(item)
            hours = int(result.group(1) or '0')
            minutes = int(result.group(2) or '0')
            return timedelta(hours=hours, minutes=minutes)

        def actually_parse_map(response):
            if response.status == 200:
                try:
                    times = map(lambda time: toTimedelta(time), response.css('div.section-directions-trip-duration::text').extract())
                    times.sort()
                    unitAtts['commute_price'] = (response.css("div.section-listbox div.section-listbox span.section-directions-trip-secondary-text[jsan='7.section-directions-trip-secondary-text']::text").extract_first() or '').encode('utf-8')
                    self.count = self.count + 1
                    self.total_move_in_fees = self.total_move_in_fees + float(unitAtts['Total Move-In Fees'])
                    self.total_rent = self.total_rent + float(unitAtts['Total Monthly Cost'])
                    self.rents.append([
                        unitAtts['url'],
                        unitAtts['Total Monthly Cost'].encode('utf-8'),
                        unitAtts['Total Move-In Fees'].encode('utf-8'),
                        str(float(unitAtts['Total Move-In Fees']) - float(unitAtts['Total Monthly Cost'])).encode('utf-8'),
                        (unitAtts.get('Deposit') or '0').encode('utf-8'),
                        (unitAtts.get('Key Money') or '0').encode('utf-8'),
                        (unitAtts.get('Agency Fee') or '0').encode('utf-8'),
                        (unitAtts.get('Guarantor Fee (Required)') or '0').encode('utf-8'),
                        (unitAtts.get('Lock Exchange Fee') or '0').encode('utf-8'),
                        (unitAtts.get('Fire Insurance') or '0').encode('utf-8'),
                        (unitAtts.get('Other') or '0').encode('utf-8'),
                        (unitAtts.get('Size') or '').encode('utf-8'),
                        (unitAtts.get('Location') or '').encode('utf-8'),
                        (str(times[0]) if len(times) > 0 else '').encode('utf-8'),
                        (unitAtts['commute_price'] or '').replace('JPY','').strip(),
                        unitAtts['directions']
                        #directions
                    ])
                    self.apartments.append(unitAtts)
                except:
                    print("Unexpected error map={}".format(sys.exc_info()))
                    raise
            else:
                print('Not ok request map:{}'.format(response.status))

        return actually_parse_map
