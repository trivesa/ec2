import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import logging
import os
import time
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import random

class ProductImageSearchBot:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.FOLDER_ID = '1LbYNBj6sW5hJuwwofxKqD1ycb4xprcyF'
        self.SHEET_ID = '1DqKSf1srmOM6Ep33WnUJ2qqLHT_wsfpkZTf2OfFaJRs'
        self.SHEET_NAME = 'sheet1'
        
        self.setup_driver()
        self.setup_google_services()
    
    def setup_google_services(self):
        """设置Google服务"""
        try:
            credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if not credentials_json:
                raise ValueError("未设置GOOGLE_APPLICATION_CREDENTIALS_JSON环境变量")
                
            credentials_info = json.loads(credentials_json)
            self.credentials = service_account.Credentials.from_service_account_info(credentials_info)
            
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            self.logger.info("Google服务初始化成功")
            
        except Exception as e:
            self.logger.error(f"设置Google服务时出错: {str(e)}")
            raise
    
    def setup_driver(self):
        """设置并初始化WebDriver"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.set_window_size(1920, 1080)
            
            self.logger.info("WebDriver初始化成功")
            
        except Exception as e:
            self.logger.error(f"设置WebDriver时出错: {str(e)}")
            raise

    def inject_image_search_input(self, image_path):
        """使用JavaScript注入图片搜索输入"""
        js_code = """
        const input = document.createElement('input');
        input.type = 'file';
        input.style.display = 'none';
        document.body.appendChild(input);
        return input;
        """
        file_input = self.driver.execute_script(js_code)
        file_input.send_keys(os.path.abspath(image_path))
        return file_input

    def search_image_with_retry(self, image_path, max_retries=3):
        """带重试机制的图片搜索"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"尝试搜索图片 (尝试 {attempt + 1}/{max_retries}): {image_path}")
                
                # 直接访问Google图片搜索上传页面
                self.driver.get("https://images.google.com/imghp?hl=en&authuser=0&ogbl")
                time.sleep(3)
                
                try:
                    # 尝试多个可能的选择器来定位相机图标
                    selectors = [
                        "div.nDcEnd",
                        "div.ZaFQO",
                        "div[aria-label='搜索图片']",
                        "div[aria-label='Search by image']",
                        "span.FRuiCf"
                    ]
                    
                    camera_button = None
                    for selector in selectors:
                        try:
                            camera_button = self.wait.until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if camera_button:
                                break
                        except:
                            continue
                    
                    if camera_button:
                        camera_button.click()
                        time.sleep(2)
                        
                        # 然后上传图片
                        file_input = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                        )
                        file_input.send_keys(os.path.abspath(image_path))
                    else:
                        raise Exception("未找到相机图标")
                    
                except Exception as e:
                    self.logger.warning(f"常规方法失败，尝试JavaScript注入: {str(e)}")
                    self.inject_image_search_input(image_path)
                
                # 等待搜索结果加载
                time.sleep(5)
                
                # 尝试获取搜索结果
                try:
                    # 等待搜索结果容器加载
                    result_container = self.wait.until(
                        EC.presence_of_element_located((By.ID, "search"))
                    )
                    
                    # 获取所有结果链接
                    results = []
                    links = self.driver.find_elements(By.CSS_SELECTOR, "a.VFACy, div.isv-r a")
                    
                    for link in links[:5]:  # 只取前5个结果
                        try:
                            url = link.get_attribute("href")
                            title = link.text or link.get_attribute("title")
                            
                            if url and title:
                                results.append({
                                    'url': url,
                                    'title': title
                                })
                                self.logger.info(f"找到结果: {title} - {url}")
                        except:
                            continue
                    
                    if results:
                        return results
                    
                except Exception as e:
                    self.logger.error(f"获取搜索结果时出错: {str(e)}")
                
            except Exception as e:
                self.logger.error(f"搜索出错 (尝试 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info("重启WebDriver并重试...")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    time.sleep(random.uniform(3, 6))
                    self.setup_driver()
                else:
                    self.logger.error("达到最大重试次数")
                    return []
        
        return []

    def extract_product_info(self, search_results):
        """从搜索结果中提取产品信息"""
        try:
            for result in search_results:
                url = result.get('url', '')
                title = result.get('title', '').lower()
                
                # 提取品牌和产品编号
                # 这里需要根据实际情况调整正则表达式
                brand_match = re.search(r'(nike|adidas|puma|gucci|louis\s*vuitton|chanel|hermes|rolex)', title, re.I)
                item_code_match = re.search(r'[A-Z0-9]{5,}', title)
                
                if brand_match:
                    return {
                        'brand': brand_match.group(1).title(),
                        'item_code': item_code_match.group(0) if item_code_match else '',
                        'url': url,
                        'url2': ''  # 可以添加第二个相关URL
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"提取产品信息时出错: {str(e)}")
            return None

    def write_to_sheets(self, results):
        """将结果写入Google Sheets"""
        try:
            range_name = f'{self.SHEET_NAME}!A2:D'
            
            body = {
                'values': results
            }
            
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.SHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.logger.info(f"成功写入 {len(results)} 条数据到表格")
            
        except Exception as e:
            self.logger.error(f"写入数据到表格时出错: {str(e)}")

    def process_folder_images(self):
        """处理文件夹中的图片"""
        try:
            query = f"'{self.FOLDER_ID}' in parents and mimeType contains 'image/'"
            files = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType)"
            ).execute().get('files', [])
            
            self.logger.info(f"找到 {len(files)} 个图片文件")
            
            file_groups = {}
            pattern = r'Additional_Image_Row_(\d+)_No_\d+'
            
            for file in files:
                match = re.match(pattern, file['name'])
                if match:
                    row_num = match.group(1)
                    if row_num not in file_groups:
                        file_groups[row_num] = []
                    file_groups[row_num].append(file)
            
            results = []
            
            for row_num in sorted(file_groups.keys(), key=int):
                self.logger.info(f"\n处理第 {row_num} 行的图片组...")
                group_files = sorted(file_groups[row_num], key=lambda x: x['name'])
                
                for file in group_files:
                    try:
                        request = self.drive_service.files().get_media(fileId=file['id'])
                        image_content = io.BytesIO()
                        downloader = MediaIoBaseDownload(image_content, request)
                        done = False
                        while done is False:
                            _, done = downloader.next_chunk()
                        
                        temp_path = f"/tmp/{file['name']}"
                        with open(temp_path, 'wb') as f:
                            f.write(image_content.getvalue())
                        
                        search_results = self.search_image_with_retry(temp_path)
                        
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                        
                        if search_results:
                            self.logger.info(f"找到搜索结果: {search_results}")
                            product_info = self.extract_product_info(search_results)
                            if product_info:
                                results.append([
                                    product_info.get('brand', ''),
                                    product_info.get('item_code', ''),
                                    product_info.get('url', ''),
                                    product_info.get('url2', '')
                                ])
                                # 写入当前结果到表格
                                self.write_to_sheets([results[-1]])
                                break
                        
                        time.sleep(random.uniform(2, 4))
                        
                    except Exception as e:
                        self.logger.error(f"处理文件 {file['name']} 时出错: {str(e)}")
                        continue
            
        except Exception as e:
            self.logger.error(f"处理文件夹时出错: {str(e)}")
            
        finally:
            try:
                self.driver.quit()
            except:
                pass

if __name__ == "__main__":
    bot = ProductImageSearchBot()
    bot.process_folder_images()
