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
    
    # 测试数据
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Please write a simple 'Hello, World!' message."
            }
        ],
        "max_tokens": 100,
        "temperature": 0.2,
        "top_p": 0.9,
        "return_images": False,
        "return_related_questions": False,
        "frequency_penalty": 1,
        "presence_penalty": 0,
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

        # 验证响应格式
        if not all(key in response_data for key in ['id', 'model', 'choices', 'usage']):
            logging.error("Response missing required fields")
            return False

        # 获取生成的内容
        content = response_data['choices'][0]['message']['content']
        logging.info(f"Generated content: {content}")

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

