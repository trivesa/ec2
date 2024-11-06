import scrapy
from scrapy.http import FormRequest

class VestiaireSpider(scrapy.Spider):
    name = "vestiaire_spider"
    allowed_domains = ["vestiairecollective.com"]
    start_urls = ["https://www.vestiairecollective.com/"]

    def parse(self, response):
        # 点击"Sign in"按钮
        login_url = response.css('a[href*="login"]::attr(href)').get()
        if login_url:
            yield scrapy.Request(url=response.urljoin(login_url), callback=self.login_page)

    def login_page(self, response):
        # 在登录页面输入邮箱
        return FormRequest.from_response(
            response,
            formdata={'email': 'info@trivesa.it'},
            clickdata={'name': 'continue'},
            callback=self.enter_password
        )

    def enter_password(self, response):
        # 输入密码并登录
        return FormRequest.from_response(
            response,
            formdata={'password': 'Milanotre@2023'},
            clickdata={'name': 'login'},
            callback=self.after_login
        )

    def after_login(self, response):
        # 检查登录是否成功
        if "My Account" not in response.text:
            self.logger.error("登录失败")
            return

        # 进入Catalogue Management页面
        catalog_url = "https://www.vestiairecollective.com/sell/catalog-management/?page=1&limit=20&sortBy=default"
        yield scrapy.Request(url=catalog_url, callback=self.parse_catalog)

    def parse_catalog(self, response):
        # 获取所有产品缩略图链接
        product_links = response.css('a.product-card::attr(href)').getall()
        for link in product_links:
            yield scrapy.Request(url=response.urljoin(link), callback=self.parse_product)

        # 处理下一页
        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield scrapy.Request(url=response.urljoin(next_page), callback=self.parse_catalog)

    def parse_product(self, response):
        # 提取产品页面的所有图片链接
        image_links = response.css('div.product-images img::attr(src)').getall()
        for link in image_links:
            yield {'image_url': link}
