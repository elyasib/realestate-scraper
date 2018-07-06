import scrapy

class SearchSpyder(scrapy.Spider):
    name = "search"
    start_urls = [
        "https://www.realestate.co.jp/en/rent/listing?prefecture=JP-13&city=&trainline=&district=&station=&min_price=100000&max_price=200000&min_meter=40&rooms=15&distance_station=&agent_id=&building_type=&building_age=&updated_within=&transaction_type=&pets=1&search=Search"
    ]

    def __init__(self, filename=None, **kwargs):
        super(SearchSpyder, self).__init__()
        self.apartments = []
        self.move_in_fees = []
        self.rents = []
        self.rents.append([
                u'url',
                u'Total Monthly Cost',
                u'Total Move-In Fees',
                u'Total Move-In Fees - Total Monthly Cost',
                u'Deposit',
                u'Key Money',
                u'Agency Fee',
                u'Guarantor Fee (Required)',
                u'Lock Exchange Fee',
                u'Fire Insurance',
                u'Other',
                u'Size',
                u'Location',
                u'Directions'
        ])
        self.total_move_in_fees = 0.0
        self.total_rent = 0.0
        self.count = 0
        self.directions = u'https://www.google.com/maps/dir/?api=1&travelmode=transit&destination=35.6619147,139.7361128&origin='

    def parse(self, response):
        if response.status == 200:
            viewLinks = response.css("body.lang-en div#top.container div.row div.col-md-8 div.rej-property-list div.property-listing").xpath("//div[contains(@class, 'listing-body')]/div[contains(@class, 'listing-left-col')]/a/@href").extract()
            dedupViewLinks = list(set(viewLinks))

            # follow rent view
            for viewLink in dedupViewLinks :
                if viewLink is not None:
                    viewUrl = response.urljoin(viewLink)
                    yield scrapy.Request(viewUrl, callback=self.parse_view)

            # follow next page
            for next in response.css("body.lang-en div#top.container div.row ul.paginator li.pagination-next")[0].css("a::attr(href)"):
                yield response.follow(next, self.parse)

    def parse_view(self, response):
        if response.status == 200:
            unitAtts = {}
            unitAtts["url"] = response.url

            # Details
            detailsTable = response.xpath("/html/body/div[3]/div[2]/div[1]/div/div[3]/div[1]/dl")
            detailNames = detailsTable.css("dt::text").extract()
            detailValues = detailsTable.css("dd::text").extract()

            for index in range(len(detailNames)):
                unitAtts[detailNames[index].strip()] = detailValues[index].strip()

            # Rent & Fees
            feesTable = response.xpath("/html/body/div[3]/div[2]/div[1]/div/div[3]/div[3]/div[2]/dl")
            feesNames = feesTable.css("dt::text").extract()
            feesValues = feesTable.css("dd::text").extract()

            for index in range(len(feesNames)):
                unitAtts[feesNames[index].encode('ascii', 'ignore').strip().encode('utf-8')] = feesValues[index].encode('ascii', 'ignore').strip().lstrip(u'\xa5').replace(',','').encode('utf-8')
                

            # Directions
            gmap = response.css("div.js-rej-map")
            lat = gmap.css("::attr('data-lat')").extract_first()
            lng = gmap.css("::attr('data-lng')").extract_first()
            address = gmap.css("::attr('data-address')").extract_first().encode('utf-8')
            directions = self.directions.encode('utf-8')
            if lat == '' or lng == '' or float(lat) == 0.0  or float(lng) == 0.0:
                directions = (directions + address)
            else:
                directions = (directions + lat + "," + lng).encode('utf-8')

            self.count = self.count + 1
            self.total_move_in_fees = self.total_move_in_fees + float(unitAtts['Total Move-In Fees'])
            self.total_rent = self.total_rent + float(unitAtts['Total Monthly Cost'])
            #self.move_in_fees.append({"url": unitAtts['url'], "value": float(unitAtts['Total Move-In Fees'])})
            #self.rents.append({"url": unitAtts['url'], "value": float(unitAtts['Total Monthly Cost'])})
            self.rents.append([
                unitAtts['url'],
                unitAtts['Total Monthly Cost'].encode('utf-8'),
                unitAtts['Total Move-In Fees'].encode('utf-8'),
                str(float(unitAtts['Total Move-In Fees']) - float(unitAtts['Total Monthly Cost'])).encode('utf-8'),
                (unitAtts.get('Deposit') or "0").encode('utf-8'),
                (unitAtts.get('Key Money') or "0").encode('utf-8'),
                (unitAtts.get('Agency Fee') or "0").encode('utf-8'),
                (unitAtts.get('Guarantor Fee (Required)') or "0").encode('utf-8'),
                (unitAtts.get('Lock Exchange Fee') or "0").encode('utf-8'),
                (unitAtts.get('Fire Insurance') or "0").encode('utf-8'),
                (unitAtts.get('Other') or "0").encode('utf-8'),
                (unitAtts.get('Size') or "").encode('utf-8'),
                (unitAtts.get('Location') or "").encode('utf-8'),
                directions
            ])
            self.apartments.append(unitAtts)

            # order them by total move-in fees
            # get the mean move-in fee
            # get the 
 
            #filename = 'quotes-%s'
            #with open(filename, 'wb') as f:
            #    f.write(response.body)
            #self.log('Saved file %s' % filename)

