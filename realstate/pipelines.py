# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import csv


class RealstatePipeline(object):
    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        spider.logger.info('Spider closed: %s', spider.name)
        #spider.logger.info('Spider closed apartments: %s', str(spider.apartments))
        spider.logger.info('Spider mean move-in fee: %s', str(spider.total_move_in_fees / spider.count))
        spider.logger.info('Spider mean monthly rent: %s', str(spider.total_rent / spider.count))
        #move_in_fees = spider.move_in_fees
        #move_in_fees.sort(key=lambda item: item["value"])
        #spider.logger.info('Spider move-in fees: %s', str(move_in_fees))
        #rents = spider.rents
        #rents.sort(key=lambda item: item["value"])
        #spider.logger.info('Spider monthly rent: %s', str(rents))
        spider.logger.info('Spider count: %s', str(spider.count))
        with open("./results.csv", "w") as output:
            writer = csv.writer(output, lineterminator='\n')
            writer.writerows(spider.rents)
