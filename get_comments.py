import requests
import time
import json
import os

def get_video_context(bvid, headers):
    """提取视频 OID (aid) 及基础指标"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] != 0:
            print(f"元数据接口拒绝: {data['message']}")
            return None
            
        return {
            "oid": data['data']['aid'],
            "title": data['data']['title']
        }
    except Exception as e:
        print(f"元数据提取异常: {e}")
        return None

def fetch_sub_replies(oid, root_id, headers, max_sub_pages=1):
    """基于根评论 ID 提取其下的二级子评论"""
    url = "https://api.bilibili.com/x/v2/reply/reply"
    sub_comments_data = []
    
    for pn in range(1, max_sub_pages + 1):
        params = {
            "oid": oid,
            "type": 1,
            "root": root_id,
            "pn": pn,
            "ps": 20
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code != 200:
                break
                
            data = response.json()
            if data['code'] != 0:
                break
                
            replies = data['data'].get('replies')
            if not replies:
                break
                
            for sub in replies:
                sub_comments_data.append({
                    "user": sub['member']['uname'],
                    "content": sub['content']['message'].replace('\n', ' '),
                    "likes": sub['like'],
                    "time": sub['ctime'],
                    "type": "sub_reply",
                    "parent_id": root_id
                })
            
            if len(replies) < 20:
                break
                
            time.sleep(1.5) 
            
        except Exception as e:
            print(f"子节点 {root_id} 提取异常: {e}")
            break
            
    return sub_comments_data

def fetch_comments_to_file(oid, title, headers, max_root_pages=5, max_sub_pages=1):
    """提取一级与二级评论并流式落盘，返回文件的绝对路径"""
    url = "https://api.bilibili.com/x/v2/reply/main"
    next_offset = 0
    collected_data = []
    
    print(f"开始提取目标: {title} (OID: {oid})")
    
    for page in range(1, max_root_pages + 1):
        params = {
            "mode": 3,
            "next": next_offset,
            "oid": oid,
            "plat": 1,
            "type": 1
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != 0:
                print(f"主评论接口异常: {data['message']}")
                break
                
            replies = data['data'].get('replies')
            if not replies:
                print("未检测到更多一级评论。")
                break
                
            for reply in replies:
                root_id = reply['rpid']
                reply_count = reply.get('rcount', 0)
                
                collected_data.append({
                    "user": reply['member']['uname'],
                    "content": reply['content']['message'].replace('\n', ' '),
                    "likes": reply['like'],
                    "time": reply['ctime'],
                    "type": "root_reply",
                    "root_id": root_id
                })
                
                if reply_count > 0 and max_sub_pages > 0:
                    sub_replies = fetch_sub_replies(oid, root_id, headers, max_sub_pages)
                    collected_data.extend(sub_replies)
            
            print(f"主页面 {page} 遍历完毕，当前总计 {len(collected_data)} 条记录。")
            
            cursor = data['data'].get('cursor')
            if not cursor or cursor.get('is_end'):
                break
                
            next_offset = cursor.get('next')
            time.sleep(2) 
            
        except Exception as e:
            print(f"主评论提取中断: {e}")
            break
            
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = os.path.join(script_dir, f"bilibili_{oid}_full.json")
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(collected_data, f, ensure_ascii=False, indent=4)
        
    print(f"数据链路终止。共落盘 {len(collected_data)} 条文本至 {output_filename}。")
    
    # 核心变更：返回物理路径以供下游管道读取
    return output_filename

def scrape_bilibili_comments(bvid, max_root_pages=5, max_sub_pages=1):
    """
    供外部调用的标准化提取接口。
    接收 BVID 参数，返回生成的 JSON 文件绝对路径。若失败则返回 None。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }
    
    context = get_video_context(bvid, headers)
    if context:
        return fetch_comments_to_file(
            context['oid'], 
            context['title'], 
            headers, 
            max_root_pages, 
            max_sub_pages
        )
    else:
        print(f"致命错误：无法提取 {bvid} 的前置上下文。")
        return None

# 保留测试入口，仅在直接运行该脚本时触发
if __name__ == "__main__":
    test_bvid = input("请输入要测试抓取的 BVID: ").strip()
    result_path = scrape_bilibili_comments(test_bvid)
    if result_path:
        print(f"测试完成，文件已生成: {result_path}")