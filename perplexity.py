import os
import logging
import requests
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_perplexity_api():
    # 获取API密钥
    api_key = os.environ.get('PERPLEXITY_API_KEY')
    if not api_key:
        logging.error("PERPLEXITY_API_KEY not found in environment variables")
        return False

    # API配置
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 测试数据 - 使用更强制性的提示
    test_string = "Hello, World!"
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": """You are a precise text replication system. Your only job is to output exactly what you are given.
                Rules:
                1. Output the exact characters provided
                2. Include ALL punctuation marks
                3. Do not add or remove anything
                4. Do not explain or comment"""
            },
            {
                "role": "user",
                "content": f"Copy this text exactly (13 characters including punctuation): {test_string}"
            }
        ],
        "max_tokens": 50,
        "temperature": 0,
        "top_p": 1.0,
        "return_images": False,
        "return_related_questions": False,
        "frequency_penalty": 0.1,
        "stream": False
    }

    try:
        # 发送请求
        logging.info("Sending test request to Perplexity API...")
        response = requests.post(url, json=payload, headers=headers)
        
        # 检查状态码
        if response.status_code != 200:
            logging.error(f"API request failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False

        # 解析响应
        response_data = response.json()
        
        # 打印完整响应以供调试
        logging.info(f"Full API Response:\n{json.dumps(response_data, indent=2)}")

        # 获取生成的内容
        content = response_data['choices'][0]['message']['content'].strip()
        logging.info(f"Generated content: {content}")

        # 详细的内容验证
        expected_content = test_string
        if content != expected_content:
            logging.warning(f"Content does not exactly match expected content")
            logging.warning(f"Expected: '{expected_content}'")
            logging.warning(f"Received: '{content}'")
            logging.warning(f"Length - Expected: {len(expected_content)}, Received: {len(content)}")
            
            # 字符级别的比较
            for i, (exp_char, rec_char) in enumerate(zip(expected_content, content + ' ' * (len(expected_content) - len(content)))):
                if exp_char != rec_char:
                    logging.warning(f"Mismatch at position {i}: Expected '{exp_char}', Received '{rec_char}'")
        else:
            logging.info("✅ Content exactly matches expected output")
        
        # 检查是否因为 token 限制而被截断
        if response_data['choices'][0]['finish_reason'] == 'length':
            logging.warning("Response was truncated due to token limit")

        # 打印使用情况
        usage = response_data['usage']
        logging.info(f"Token usage - Prompt: {usage['prompt_tokens']}, "
                    f"Completion: {usage['completion_tokens']}, "
                    f"Total: {usage['total_tokens']}")

        return True

    except Exception as e:
        logging.error(f"Test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Starting Perplexity API test...")
    success = test_perplexity_api()
    if success:
        logging.info("✅ Test completed successfully!")
    else:
        logging.error("❌ Test failed!")
