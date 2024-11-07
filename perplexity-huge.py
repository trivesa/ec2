import json
import os
import time
from typing import Optional, Dict, List, Any, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import logging
from logging.handlers import RotatingFileHandler
import re

# 改进的日志设置
def setup_logging():
    """设置增强的日志记录"""
    log_file = 'perplexity_script.log'
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

setup_logging()

# API配置和验证
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

# 验证环境变量
required_vars = {
    'GOOGLE_APPLICATION_CREDENTIALS': '谷歌认证凭据路径',
    'PERPLEXITY_API_KEY': 'Perplexity API密钥',
    'SPREADSHEET_ID': '电子表格ID'
}

missing_vars = [var for var, desc in required_vars.items() if not os.environ.get(var)]
if missing_vars:
    for var in missing_vars:
        logging.error(f"缺少必需的环境变量: {var} ({required_vars[var]})")
    exit(1)

# 设置Google Sheets API
try:
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    sheets_service = build('sheets', 'v4', credentials=credentials)
except Exception as e:
    logging.error(f"初始化Google Sheets API时出错: {str(e)}")
    exit(1)

def get_size_info(size_row: List[str]) -> str:
    """处理尺码信息"""
    if not size_row:
        return ""
    
    sizes = []
    for size in size_row:
        if size and str(size).strip() != "":
            sizes.append(str(size).strip())
    
    return ", ".join(sizes) if sizes else ""

def read_spreadsheet(range_name: str) -> List[List[str]]:
    """从电子表格读取数据"""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logging.info(f"从{range_name}读取了{len(values)}行数据")
        
        if not values:
            logging.warning(f"在{range_name}中未找到数据")
        
        return values
    except Exception as e:
        logging.error(f"读取电子表格时出错 ({range_name}): {str(e)}")
        raise

def write_to_spreadsheet(range_name: str, values: List[List[Any]]) -> bool:
    """写入数据到电子表格"""
    try:
        body = {
            'values': [
                [str(cell) if cell is not None else 'N/A' for cell in row]
                for row in values
            ]
        }
        
        logging.info(f"尝试写入{len(values)}行到范围: {range_name}")
        if values:
            logging.info(f"第一行数据示例: {values[0]}")
        
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        updated_cells = result.get('updatedCells', 0)
        logging.info(f"成功更新了{updated_cells}个单元格")
        return True
        
    except Exception as e:
        logging.error(f"写入电子表格时出错: {str(e)}")
        return False
class PerplexityAPI:
    """Perplexity API处理类"""
    def __init__(self, api_key: str, base_url: str = 'https://api.perplexity.ai/chat/completions'):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self.error_count = 0
        self.max_errors = 5

    def call_api(self, prompt: str, temperature: float = 0.3, 
                max_retries: int = 3, retry_delay: int = 5) -> Optional[str]:
        """调用Perplexity API"""
        data = {
            'model': 'llama-3.1-sonar-huge-128k-online',
            'messages': [
                {
                    'role': 'system',
                    'content': '''You are a luxury fashion expert specializing in high-end product descriptions.
                    Your responses should be:
                    1. Professional but accessible
                    2. Accurate and specific
                    3. Free of marketing hyperbole
                    4. Focused on materials, craftsmanship, and design
                    5. Compliant with EU/UK product description standards'''
                },
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1000,
            'temperature': temperature,
            'top_p': 0.9,
            'return_citations': True,
            'frequency_penalty': 1
        }

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.base_url,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                
                response_json = response.json()
                content = response_json['choices'][0]['message']['content']
                
                self._save_api_response(response_json)
                logging.info(f"API调用成功 (尝试 {attempt + 1}/{max_retries})")
                self.error_count = 0  # 重置错误计数
                return content
                
            except Exception as e:
                self._handle_api_error(e, attempt, max_retries)
                self.error_count += 1
                
                if self.error_count >= self.max_errors:
                    logging.error("达到最大错误次数，停止处理")
                    return None
            
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)
                time.sleep(sleep_time)
        
        logging.error(f"在{max_retries}次尝试后API调用失败")
        return None

    def _handle_api_error(self, error: Exception, attempt: int, max_retries: int) -> None:
        """处理API错误"""
        if isinstance(error, requests.exceptions.Timeout):
            logging.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries})")
        elif isinstance(error, requests.exceptions.RequestException):
            logging.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {str(error)}")
        else:
            logging.error(f"未预期的错误 (尝试 {attempt + 1}/{max_retries}): {str(error)}")

    def generate_description_prompt(self, brand: str, product_type: str, 
                                  style_number: str, additional_info: str) -> str:
        """生成产品描述提示"""
        return f"""
        Generate a concise product description in HTML format for a {brand} {product_type} with style number {style_number}.
        Additional Information: {additional_info}
        
        Requirements:
        1. Format:
            - Title: Brand + Product Type + Key Feature (max 80 characters)
            - Short description: 2-3 sentences about the product's unique features
            - 4-6 bullet points highlighting key features
        
        2. Content:
            - Focus on unique design elements, materials, and craftsmanship
            - Highlight what makes this product special
            - DO NOT include any shipping, payment, or return policy information
            - DO NOT include prices or promotional content
        
        3. Use this HTML structure:
            <h1>[Title]</h1>
            <p>[Short description]</p>
            <h3>Key Features:</h3>
            <ul>
                <li>[Feature 1]</li>
                <li>[Feature 2]</li>
                ...
            </ul>
        """

    def format_html_response(self, response: str) -> str:
        """格式化API响应为HTML"""
        if not response or '**' not in response:
            return response

        # 转换标题
        response = response.replace('**Title:**', '<h1>')
        response = response.replace('**Subtitle:**', '</h1>\n<h2>')
        
        # 转换关键特性
        response = response.replace('**Key Features:**', '</h2>\n<h3>Key Features:</h3>\n<ul>')
        
        # 转换列表项
        lines = response.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            if line.strip().startswith('- **'):
                if not in_list:
                    in_list = True
                line = line.replace('- **', '<li><strong>').replace('**', '</strong>')
                line = f"{line}</li>"
            elif in_list and not line.strip().startswith('-'):
                in_list = False
                formatted_lines.append('</ul>')
            formatted_lines.append(line)
        
        response = '\n'.join(formatted_lines)
        
        # 清理其余的Markdown语法和HTML标签
        response = response.replace('**', '<strong>').replace('**', '</strong>')
        response = '<p>' + response + '</p>'
        response = response.replace('\n\n', '</p>\n<p>')
        response = response.replace('<p><h', '<h')
        response = response.replace('</h1></p>', '</h1>')
        response = response.replace('</h2></p>', '</h2>')
        response = response.replace('</h3></p>', '</h3>')
        response = response.replace('</ul></p>', '</ul>')
        
        return response

    def _save_api_response(self, response_json: Dict) -> None:
        """保存API响应到文件"""
        try:
            filename = f'api_response_{int(time.time())}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response_json, f, indent=2, ensure_ascii=False)
            logging.info(f"API响应已保存到: {filename}")
        except Exception as e:
            logging.error(f"保存API响应时出错: {str(e)}")

    def retry_with_backoff(self, func, max_retries: int = 3, 
                          initial_delay: int = 1) -> Optional[Any]:
        """通用的指数退避重试机制"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = initial_delay * (2 ** attempt)
                logging.warning(f"尝试失败 ({attempt + 1}/{max_retries}), "
                              f"{delay}秒后重试: {str(e)}")
                time.sleep(delay)
class DataProcessor:
    """数据处理类"""
    def __init__(self):
        self.valid_categories = {
            'shoes': ['Athletic', 'Casual', 'Formal', 'Boots', 'Sandals'],
            'clothing': ['Shirts', 'Pants', 'Dresses', 'Jackets', 'Accessories']
        }

    def validate_product_type(self, product_type: str) -> bool:
        """验证产品类型"""
        if not product_type:
            return False
        return product_type.lower() in self.valid_categories

    def validate_brand(self, brand: str) -> bool:
        """验证品牌名称"""
        if not brand or len(brand.strip()) < 2:
            return False
        return True

    def validate_style_number(self, style_number: str) -> bool:
        """验证款式编号"""
        if not style_number or len(style_number.strip()) < 3:
            return False
        return True

    def extract_fields_from_response(self, raw_response: str, template: Dict) -> Dict[str, str]:
        """从API响应中提取字段"""
        try:
            # 尝试直接解析JSON
            try:
                data = json.loads(raw_response)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

            # 如果不是JSON，从文本提取字段
            data = {}
            current_field = None
            current_content = []
            
            lines = raw_response.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                field_match = re.match(r'\*\*(.*?):\*\*\s*(.*)', line)
                if field_match:
                    if current_field and current_content:
                        data[current_field] = '\n'.join(current_content).strip()
                        current_content = []
                    
                    current_field = field_match.group(1).strip()
                    content = field_match.group(2).strip()
                    if content:
                        current_content.append(content)
                elif current_field:
                    current_content.append(line)
            
            if current_field and current_content:
                data[current_field] = '\n'.join(current_content).strip()

            # 验证必需字段
            self._validate_extracted_data(data, template)
            
            return data
            
        except Exception as e:
            logging.error(f"提取字段时出错: {str(e)}")
            return None

    def _validate_extracted_data(self, data: Dict[str, str], template: Dict) -> None:
        """验证提取的数据"""
        if not isinstance(data, dict):
            raise ValueError("无效的数据格式：期望字典类型")

        # 检查必需字段
        missing_fields = []
        for field in template.get('mandatory_fields', []):
            if field not in data or not data[field]:
                missing_fields.append(field)
                data[field] = 'N/A'
        
        if missing_fields:
            logging.warning(f"缺少必需字段: {', '.join(missing_fields)}")

        # 验证字段长度
        if 'Title' in data and len(data['Title']) > 80:
            logging.warning(f"标题超出长度限制: {len(data['Title'])}字符")
            data['Title'] = data['Title'][:77] + '...'

class SheetManager:
    """工作表管理类"""
    def __init__(self, sheets_service, spreadsheet_id: str):
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_cache = {}

    def format_sheet_name(self, name: str) -> str:
        """格式化工作表名称"""
        # 移除特殊字符
        name = re.sub(r'[^\w\s-]', '', name)
        # 转换为小写并替换空格为下划线
        return name.lower().strip().replace(' ', '_')

    def ensure_sheet_exists(self, sheet_name: str) -> bool:
        """确保工作表存在"""
        try:
            if sheet_name in self.sheet_cache:
                return True

            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            # 检查工作表是否存在
            for sheet in sheet_metadata.get('sheets', ''):
                if sheet['properties']['title'] == sheet_name:
                    self.sheet_cache[sheet_name] = True
                    return True
            
            # 创建新工作表
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()
            logging.info(f"已创建工作表'{sheet_name}'")
            self.sheet_cache[sheet_name] = True
            return True
            
        except Exception as e:
            logging.error(f"处理工作表'{sheet_name}'时出错: {str(e)}")
            return False

    def create_sheet_if_not_exists(self, sheet_name: str) -> bool:
        """如果工作表不存在则创建"""
        formatted_name = self.format_sheet_name(sheet_name)
        if not self.ensure_sheet_exists(formatted_name):
            logging.error(f"无法创建工作表: {formatted_name}")
            return False
        return True

    def write_description_to_sheet(self, sheet_name: str, row_index: int,
                                 internal_reference: str, description: str) -> bool:
        """写入描述到工作表"""
        try:
            range_name = f"'{sheet_name}'!C{row_index}:D{row_index}"
            body = {
                'values': [[internal_reference, description]]
            }
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            logging.info(f"描述和内部参考已写入工作表'{sheet_name}'第{row_index}行")
            return True
        except Exception as e:
            logging.error(f"写入工作表'{sheet_name}'时出错: {str(e)}")
            return False

    def get_current_row(self, sheet_name: str) -> int:
        """获取工作表的当前行数"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!A:A"
            ).execute()
            return len(result.get('values', [])) + 1
        except Exception as e:
            logging.error(f"获取工作表'{sheet_name}'行数时出错: {str(e)}")
            return 2
class ProductProcessor:
    """产品处理类"""
    def __init__(self, sheet_manager: SheetManager, perplexity_api: PerplexityAPI,
                 data_processor: DataProcessor):
        """初始化ProductProcessor"""
        self.sheet_manager = sheet_manager
        self.perplexity_api = perplexity_api
        self.data_processor = data_processor
        self.processed_count = 0
        self.max_retries = 3

    def process_product(self, product_type: str, brand: str, style_number: str,
                       additional_info: str, size_info: str, index: int,
                       max_retries: int = 2) -> Optional[Tuple[str, Dict[str, str]]]:
        """处理单个产品"""
        logging.info(f"处理: 产品类型: '{product_type}', 品牌: '{brand}', "
                    f"款式编号: '{style_number}'")
        
        try:
            # 验证输入数据
            if not all([
                self.data_processor.validate_product_type(product_type),
                self.data_processor.validate_brand(brand),
                self.data_processor.validate_style_number(style_number)
            ]):
                logging.error("产品数据验证失败")
                return None

            # 生成产品描述
            description = self.generate_product_description(
                brand, product_type, style_number, additional_info
            )
            
            if description:
                sheet_name = self.sheet_manager.format_sheet_name(product_type)
                if not self.sheet_manager.create_sheet_if_not_exists(sheet_name):
                    logging.error(f"无法处理工作表: {sheet_name}")
                    return None

                self.sheet_manager.write_description_to_sheet(
                    sheet_name,
                    index + 2,
                    style_number,
                    description
                )
            
            # 处理其他产品数据
            template = self._get_template(product_type)
            if not template:
                return None
            
            prompt = self._generate_prompt(template, brand, product_type,
                                        style_number, additional_info, size_info)
            
            for attempt in range(max_retries):
                response = self.perplexity_api.call_api(prompt)
                if response:
                    extracted_data = self.data_processor.extract_fields_from_response(
                        response, template
                    )
                    if extracted_data:
                        self.processed_count += 1
                        if self.processed_count % 10 == 0:
                            logging.info(f"进度更新: 已处理 {self.processed_count} 个产品")
                        return product_type.lower(), extracted_data
                
                if attempt < max_retries - 1:
                    time.sleep(5)
            
            logging.error(f"处理产品失败，已重试{max_retries}次")
            return None
            
        except Exception as e:
            logging.error(f"处理产品时出错: {str(e)}")
            return None

    def generate_product_description(self, brand: str, product_type: str,
                                   style_number: str, additional_info: str) -> Optional[str]:
        """生成产品描述"""
        prompt = self.perplexity_api.generate_description_prompt(
            brand, product_type, style_number, additional_info
        )
        
        response = self.perplexity_api.call_api(prompt)
        if response:
            return self.perplexity_api.format_html_response(response)
        return None

    def _get_template(self, product_type: str) -> Optional[Dict]:
        """获取产品模板"""
        if not product_type:
            logging.error("产品类型为空")
            return None
        
        product_type = product_type.lower().strip()
        
        # 基础模板
        template = {
            'mandatory_fields': [
                'Title', 'Subtitle', 'Short Description', 'Description',
                'Brand', 'Style', 'Color', 'Material', 'Condition'
            ],
            'optional_fields': [
                'Pattern', 'Features', 'Occasion', 'Season',
                'Style Code', 'Department', 'Theme'
            ]
        }
        
        # 鞋类特定字段
        if product_type == 'shoes':
            template['mandatory_fields'].extend([
                'Heel Height', 'Shoe Size', 'Country/Region of Manufacture'
            ])
            template['optional_fields'].extend([
                'Width', 'US Shoe Size', 'EUR Shoe Size',
                'UK Shoe Size', 'Heel Type', 'Sole Material'
            ])
        
        return template
class ProductProcessor:
    def _generate_prompt(self, template: Dict, brand: str, product_type: str,
                        style_number: str, additional_info: str, size_info: str) -> str:
        """生成API提示"""
        if product_type.lower() == 'shoes':
            prompt = f"""
            Please provide detailed information about these {brand} shoes.
            Style Number: {style_number}
            Additional Information: {additional_info}
            Available Sizes: {size_info}

            Required Fields:
            - Title: Create a clear title under 80 characters including brand, type, and key features
            - Subtitle: Create a compelling subtitle under 55 characters
            - Short Description: 2-3 sentences summarizing key features
            - Description: Detailed, professional description including:
              * Design and style details
              * Materials and construction
              * Comfort features
              * Sizing and fit information
              * Care instructions
            
            Technical Specifications:
            - Brand: {brand}
            - Style Number: {style_number}
            - Available Sizes: {size_info}
            - Include all available information about:
              * Color
              * Material
              * Heel Height
              * Sole Material
              * Country of Manufacture
              * Width (if applicable)
              * Pattern (if applicable)
              * Season (if applicable)
            
            Additional Notes:
            {additional_info}

            Please format the response as a structured JSON object with all the fields.
            """
        else:
            prompt = f"""
            Please generate a detailed product listing for this {brand} {product_type}.
            Style Number: {style_number}
            Additional Information: {additional_info}
            Size Information: {size_info}

            Required Fields:
            """
            
            for field in template['mandatory_fields']:
                prompt += f"\n- {field}"
            
            prompt += "\n\nOptional Fields (include if information is available):"
            for field in template['optional_fields']:
                prompt += f"\n- {field}"
            
            prompt += f"""

            Guidelines:
            1. Title must be under 80 characters
            2. Subtitle must be under 55 characters
            3. Include all available technical specifications
            4. Maintain professional tone
            5. Format response as JSON
            
            Additional Notes:
            {additional_info}
            """
        
        return prompt

def clean_row_data(row_data: Dict[str, str]) -> Dict[str, str]:
    """清理行数据"""
    return {
        key: value.strip() if isinstance(value, str) else str(value)
        for key, value in row_data.items()
    }

def validate_row_data(row_data: Dict[str, str], data_processor: DataProcessor) -> bool:
    """增强的数据验证"""
    if not row_data['style_number'].strip():
        logging.warning("款式编号为空")
        return False
        
    if not row_data['brand'].strip():
        logging.warning("品牌名称为空")
        return False
        
    if len(row_data['style_number']) < 3:
        logging.warning(f"款式编号过短: {row_data['style_number']}")
        return False
        
    return all([
        data_processor.validate_product_type(row_data['product_type']),
        data_processor.validate_brand(row_data['brand']),
        data_processor.validate_style_number(row_data['style_number'])
    ])

def main():
    """主函数"""
    try:
        # 初始化组件
        sheet_manager = SheetManager(sheets_service, SPREADSHEET_ID)
        perplexity_api = PerplexityAPI(PERPLEXITY_API_KEY)
        data_processor = DataProcessor()
        product_processor = ProductProcessor(sheet_manager, perplexity_api, data_processor)

        # 读取数据
        spreadsheet_ranges = {
            'product_types': 'Sheet1!E2:E',
            'brands': 'Sheet1!F2:F',
            'style_numbers': 'Sheet1!I2:I',
            'additional_info': 'Sheet1!G2:G',
            'size_info': 'Sheet1!K2:X',
            'internal_references': 'Sheet1!C2:C'
        }
        
        data = {key: read_spreadsheet(range_name) 
                for key, range_name in spreadsheet_ranges.items()}
        
        # 验证数据
        min_length = min(len(data['product_types']), len(data['brands']),
                        len(data['style_numbers']), len(data['internal_references']))
        
        if min_length == 0:
            logging.error("一个或多个必需列为空。请检查电子表格。")
            return

        # 处理每行数据
        sheet_data = {}
        for index in range(min_length):
            try:
                row_data = {
                    'product_type': str(data['product_types'][index][0]).strip() if data['product_types'][index] else "",
                    'brand': str(data['brands'][index][0]).strip() if data['brands'][index] else "",
                    'style_number': str(data['style_numbers'][index][0]).strip() if data['style_numbers'][index] else "",
                    'additional_info': str(data['additional_info'][index][0]).strip() if index < len(data['additional_info']) and data['additional_info'][index] else "",
                    'size_info': str(data['size_info'][index][0]).strip() if index < len(data['size_info']) and data['size_info'][index] else "",
                    'internal_reference': str(data['internal_references'][index][0]).strip() if data['internal_references'][index] else ""
                }

                # 清理和验证数据
                row_data = clean_row_data(row_data)
                if not validate_row_data(row_data, data_processor):
                    logging.warning(f"跳过第{index+2}行：数据验证失败")
                    continue

                result = product_processor.process_product(
                    row_data['product_type'], row_data['brand'],
                    row_data['style_number'], row_data['additional_info'],
                    row_data['size_info'], index
                )

                if result:
                    sheet_name, extracted_data = result
                    if sheet_name not in sheet_data:
                        sheet_data[sheet_name] = []
                    extracted_data['Internal Reference'] = row_data['internal_reference']
                    sheet_data[sheet_name].append(extracted_data)

            except Exception as e:
                logging.error(f"处理第{index + 2}行时出错: {str(e)}")
                continue

        # 写入数据到工作表
        for sheet_name, data_list in sheet_data.items():
            if not write_to_spreadsheet(f"'{sheet_name}'!A{len(data_list) + 1}", data_list):
                logging.error(f"写入数据到工作表{sheet_name}失败")

    except Exception as e:
        logging.error(f"主程序执行出错: {str(e)}")
        raise

if __name__ == '__main__':
    main()
