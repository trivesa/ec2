import scrapy
from scrapy.http import FormRequest

class VestiaireSpider(scrapy.Spider):
    name = "vestiaire_spider"
    allowed_domains = ["us.vestiairecollective.com"]
    start_urls = ["https://us.vestiairecollective.com/login/"]

    def parse(self, response):
        # 提取登录表单的必要字段
        return FormRequest.from_response(
            response,
            formdata={
                'email': 'info@trivesa.it',
                'password': 'Milanotre@2023'
            },
            callback=self.after_login
        )

    def after_login(self, response):
        # 检查是否登录成功
        if "认证失败" in response.text:
            self.logger.error("登录失败")
            return

        # 登录成功，前往目标页面
        yield scrapy.Request(
            url="https://www.vestiairecollective.com/sell/catalog-management/?page=1&limit=20&sortBy=default",
            callback=self.parse_target_page
        )

    def parse_target_page(self, response):
        # 提取图片链接
        image_links = response.css('img::attr(src)').getall()
        for link in image_links:
            yield {'https://www.vestiairecollective.com/women-shoes/flats/jimmy-choo/silver-glitter-jimmy-choo-flats-44125952.shtml': link}

        # 如果有下一页，继续爬取
        next_page = response.css('下一页按钮的CSS选择器::attr(href)').get()
        if next_page:
            yield scrapy.Request(url=response.urljoin(next_page), callback=self.parse_target_page)
