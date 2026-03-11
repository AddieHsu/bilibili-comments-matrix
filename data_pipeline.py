import json
import re
import os

def clean_scraped_data(input_filepath):
    """
    供外部调用的标准化清洗接口。
    接收原始 JSON 的物理路径，返回清洗后新 JSON 的物理路径。
    """
    if not input_filepath or not os.path.exists(input_filepath):
        print("致命错误：清洗层未接收到有效的上游数据源。")
        return None

    # 动态生成输出文件名 (例如在原文件名后追加 _cleaned)
    dir_name = os.path.dirname(input_filepath)
    base_name = os.path.basename(input_filepath)
    name_part, ext_part = os.path.splitext(base_name)
    output_filepath = os.path.join(dir_name, f"{name_part}_cleaned{ext_part}")

    # 预编译正则表达式
    reply_pattern = re.compile(r'^回复\s*@([^:：]+)[:：]\s*')
    emoticon_pattern = re.compile(r'\[.*?\]')
    filler_pattern = re.compile(r'（）|\(\)')
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]')
    
    stop_words = {"打卡", "第一", "前排", "好耶", "蹲一个", "卧槽", "太棒了"}

    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"清洗层 I/O 异常，无法读取上游数据: {e}")
        return None

    cleaned_data = []

    for item in raw_data:
        original_text = item.get('content', '')
        
        target_user = None
        match = reply_pattern.search(original_text)
        if match:
            target_user = match.group(1).strip()
            
        text = reply_pattern.sub('', original_text)
        text = emoticon_pattern.sub('', text)
        text = filler_pattern.sub('', text)
        text = text.strip()
        
        if len(text) < 4:
            continue
            
        if any(word in text for word in stop_words):
            continue
            
        chinese_chars = chinese_pattern.findall(text)
        if len(text) > 0 and (len(chinese_chars) / len(text)) < 0.3:
            continue
            
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)

        cleaned_data.append({
            "user": item.get('user'),
            "reply_to": target_user,
            "content": text,
            "likes": item.get('likes', 0),
            "type": item.get('type')
        })

    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

    return output_filepath