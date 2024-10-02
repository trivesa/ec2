import scrapy


class VestiaireSpiderSpider(scrapy.Spider):
    name = "vestiaire_spider"
    allowed_domains = ["us.vestiairecollective.com"]
    start_urls = ["https://us.vestiairecollective.com"]

    def parse(self, response):
        pass
