from openai import OpenAI
import json
import re
import time
import os
import concurrent.futures

# 初始化本地 LM Studio 客户端 (端口通常为 1234)
client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not-needed")

# ----------------- 1. 中间件：自愈逻辑 -----------------
def heal_and_parse_json(raw_text):
    """物理剥离与启发式语法修复"""
    text = re.sub(r'```(?:json)?', '', raw_text).strip()
    match = re.search(r'(\[.*\])', text, re.DOTALL)
    if not match: return None 
    core_json_str = match.group(1)
    
    try:
        return json.loads(core_json_str)
    except json.JSONDecodeError:
        pass
        
    healed_str = re.sub(r',\s*([\]}])', r'\1', core_json_str)
    try:
        return json.loads(healed_str)
    except json.JSONDecodeError:
        return None

# ----------------- 2. 物理层：LLM 驱动 -----------------
def call_local_qwen(prompt_payload, system_instruction):
    """
    触发本地 Qwen 9B 推理。
    """
    try:
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_payload}
            ],
            temperature=0.1, 
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"本地推理引擎物理链路断开: {e}")
        return ""

# ----------------- 3. 控制层：重试封装 -----------------
def extract_intelligence_with_retry(prompt_payload, system_instruction, max_retries=3):
    """将 LLM 调用与中间件强绑定，接收动态 Prompt"""
    for attempt in range(1, max_retries + 1):
        raw_output = call_local_qwen(prompt_payload, system_instruction)
        
        full_json_string = raw_output
        if not raw_output.strip().startswith('{') and not raw_output.strip().startswith('['):
             full_json_string = '{"data": [\n' + raw_output
             
        match = re.search(r'"data"\s*:\s*(\[.*?\])', full_json_string, re.DOTALL)
        if match:
            array_str = match.group(1)
            array_str = re.sub(r',\s*\]', ']', array_str) 
            try:
                return json.loads(array_str)
            except json.JSONDecodeError:
                pass
                
        parsed = heal_and_parse_json(full_json_string)
        if parsed: 
            return parsed

        print(f"模型输出结构坍塌。防线介入，执行第 {attempt}/{max_retries} 次重试...")
        time.sleep(1) 
        
    return []

# ----------------- 4. 并发隔离器与物理防线 -----------------
def _process_single_batch(batch, custom_system_prompt, max_chars_per_comment=400):
    """
    隔离单次批处理的内存上下文。
    max_chars_per_comment: 强制截断防线，阻断超长文本引起的 VRAM 溢出。
    """
    text_payload = "分析以下测试玩家评论，提取情报并按规定 JSON 格式输出：\n\n"
    
    for c in batch:
        raw_content = c.get('content', '')
        # 物理截断：切除超过阈值的长尾冗余信息
        if len(raw_content) > max_chars_per_comment:
            raw_content = raw_content[:max_chars_per_comment] + "...[长文本硬截断]"
            
        # 净化潜在的换行符污染，维持 Prompt 结构紧凑
        clean_content = raw_content.replace('\n', ' ').replace('\r', '')
        text_payload += f"- {clean_content}\n"
        
    text_payload += "\n\n{\n  \"data\": [\n"

    return extract_intelligence_with_retry(text_payload, custom_system_prompt)

# ----------------- 5. 外部暴露接口 (核心变更) -----------------
def extract_intelligence(input_filepath, custom_system_prompt, batch_size=10, max_workers=3):
    """
    引入线程池并发调度。
    max_workers 定义了同时向 LM Studio 发送的并发请求数。
    """
    if not input_filepath or not os.path.exists(input_filepath):
        print("致命错误：节点 C 未接收到有效载荷。")
        return None

    with open(input_filepath, 'r', encoding='utf-8') as f:
        cleaned_data = json.load(f)

    all_extracted = []
    
    # 预先拆分数据矩阵
    batches = [cleaned_data[i:i + batch_size] for i in range(0, len(cleaned_data), batch_size)]
    
    # 建立多线程并发拓扑
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 将任务压入线程池并映射系统指令
        future_to_batch = {
            executor.submit(_process_single_batch, batch, custom_system_prompt): batch 
            for batch in batches
        }
        
        # 异步捕获完成的张量结果
        for future in concurrent.futures.as_completed(future_to_batch):
            try:
                batch_result = future.result()
                if isinstance(batch_result, list):
                    all_extracted.extend(batch_result)
                elif isinstance(batch_result, dict) and "data" in batch_result:
                    all_extracted.extend(batch_result["data"])
            except Exception as exc:
                print(f"线程执行发生物理断裂: {exc}")

    valid_data = [item for item in all_extracted if item]
    
    # 动态派生输出文件名，建立物理隔离
    dir_name = os.path.dirname(input_filepath)
    base_name = os.path.basename(input_filepath)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # 剥离可能存在的 "cleaned_" 前缀以防命名无限冗长
    clean_prefix = "cleaned_"
    if name_without_ext.startswith(clean_prefix):
        name_without_ext = name_without_ext[len(clean_prefix):]
        
    output_filename = f"{name_without_ext}_intelligence.json"
    output_filepath = os.path.join(dir_name, output_filename)
    
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(valid_data, f, ensure_ascii=False, indent=4)
        
    return output_filepath