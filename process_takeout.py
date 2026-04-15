# -*- coding: utf-8 -*-
"""
YouTube Takeout 数据处理脚本
从观看记录HTML中提取视频URL和观看时间，调用API获取详情
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
import json
import zipfile
import time
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

# =============================================================================
# 配置加载
# =============================================================================

def load_config():
    """从config.json加载配置"""
    config_path = Path(__file__).parent / "config.json"
    
    if not config_path.exists():
        print("Config file not found:", config_path)
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n" + "="*60)
    print("Config Loaded")
    print("="*60)
    print(f"API Key: {config['api']['key'][:20]}...")
    print(f"Proxy: {config['api']['proxy']['http']}")
    print(f"Takeout path: {config['paths']['takeout_dir']}")
    
    return config

# =============================================================================
# 代理设置
# =============================================================================

def setup_proxy(proxy_config):
    """设置代理"""
    os.environ['HTTP_PROXY'] = proxy_config['http']
    os.environ['HTTPS_PROXY'] = proxy_config['https']
    os.environ['http_proxy'] = proxy_config['http']
    os.environ['https_proxy'] = proxy_config['https']
    print("Proxy configured")

# =============================================================================
# YouTube API 初始化
# =============================================================================

def init_youtube_api(api_key):
    """初始化YouTube API"""
    from googleapiclient.discovery import build
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    print("YouTube API initialized")
    
    return youtube

# =============================================================================
# Step 1: 创建输出文件夹
# =============================================================================

def create_output_folder(base_dir: Path):
    """创建输出文件夹，序号自动+1"""
    outcome_dir = Path(__file__).parent / "outcome"
    outcome_dir.mkdir(exist_ok=True)
    
    # 找到最大的序号
    max_num = 0
    for sub_dir in outcome_dir.iterdir():
        if sub_dir.is_dir() and sub_dir.name.isdigit():
            max_num = max(max_num, int(sub_dir.name))
    
    # 新序号
    new_num = max_num + 1
    output_dir = outcome_dir / str(new_num)
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nOutput folder: {output_dir}")
    
    return output_dir

# =============================================================================
# Step 2: 解压ZIP文件（如果需要）
# =============================================================================

def extract_zip_if_needed(takeout_dir: Path):
    """检查并解压ZIP文件"""
    print("\n" + "="*60)
    print("Step 1: Checking ZIP files")
    print("="*60)
    
    # 查找ZIP文件
    zip_files = list(takeout_dir.glob("*.zip")) + list(takeout_dir.glob("*.rar"))
    
    if not zip_files:
        print("No ZIP files found, skipping extraction")
        return True
    
    for zip_path in zip_files:
        print(f"\nFound ZIP: {zip_path.name}")
        extract_to = takeout_dir / zip_path.stem
        
        if extract_to.exists():
            print(f"  Already extracted, skipping")
            continue
        
        print(f"  Extracting to: {extract_to}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(takeout_dir)
            print("  Extraction complete!")
        except Exception as e:
            print(f"  Extraction failed: {e}")
            return False
    
    return True

# =============================================================================
# Step 3: 提取视频URL和观看时间
# =============================================================================

def find_watch_history_file(takeout_dir: Path):
    """查找观看记录HTML文件"""
    # 尝试多个可能的路径
    possible_paths = [
        takeout_dir / "YouTube 和 YouTube Music" / "历史记录",
        takeout_dir / "YouTube and YouTube Music" / "History",
        takeout_dir / "历史记录",
        takeout_dir,
    ]
    
    history_dir = None
    for path in possible_paths:
        if path.exists():
            history_dir = path
            break
    
    if not history_dir:
        return None
    
    # 查找HTML文件
    html_files = list(history_dir.glob("*.html"))
    
    for f in html_files:
        if "观看记录" in f.name or "watch" in f.name.lower():
            return f
    
    return html_files[0] if html_files else None

def extract_video_urls_with_time(history_file: Path):
    """从HTML文件中提取YouTube视频URL和观看时间"""
    print("\n" + "="*60)
    print("Step 2: Extracting Video URLs and Watch Times")
    print("="*60)
    
    print(f"\nReading file: {history_file}")
    
    # 读取HTML内容
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        try:
            with open(history_file, 'r', encoding='latin-1') as f:
                html_content = f.read()
        except Exception as e:
            print(f"Failed to read file: {e}")
            return [], {}
    
    print(f"  File size: {len(html_content):,} bytes")
    
    # 观看记录HTML的常见模式
    # 模式1: <a href="...watch?v=ID">标题</a> 后面紧跟时间
    # 模式2: 标题<br>时间 的格式
    
    # 用于存储 video_id -> watch_time 的映射（保留第一个观看时间）
    video_times = {}
    
    # 匹配模式: 视频URL后跟中文日期时间
    # 例如: <a href="https://www.youtube.com/watch?v=VIDEO_ID">...</a><br>2024年3月15日 下午2:30
    # 或者: ...watch?v=VIDEO_ID" ytid="VIDEO_ID">标题</a><br>2024年3月15日
    
    # 方法1: 提取所有视频URL及其后面的日期时间
    # 这个正则匹配 "watch?v=ID" 后跟标题和时间
    pattern1 = r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11}).*?<br>([\d年月日上下下午\s:]+)'
    
    # 方法2: 使用更简单的模式 - 找到每个watch链接后找最近的日期
    # 先找到所有 video_id 和 其后的 <br>xxx 时间
    simple_pattern = r'watch\?v=([a-zA-Z0-9_-]{11})'
    all_matches = list(re.finditer(simple_pattern, html_content))
    
    print(f"  Found {len(all_matches):,} video URLs")
    
    # 从后往前处理，提取每个video_id后的时间
    # 时间格式可能是: "2024年3月15日" 或 "2024年3月15日 下午2:30"
    time_pattern = r'([\d]{4}年[\d]+月[\d]+日)[\s]*([上下]?午[\d:]+)?'
    
    # 从HTML末尾开始往前找，因为最新的记录在前面
    processed_ids = set()
    
    for match in reversed(all_matches):
        video_id = match.group(1)
        
        # 跳过已处理的
        if video_id in processed_ids:
            continue
        
        # 查找该位置后的日期时间
        start_pos = match.end()
        search_window = html_content[start_pos:start_pos + 200]  # 往后找200字符
        
        time_match = re.search(time_pattern, search_window)
        if time_match:
            date_str = time_match.group(1)
            time_str = time_match.group(2) if time_match.group(2) else ""
            
            watch_time = f"{date_str} {time_str}".strip()
            
            # 如果还没记录过这个视频的时间，保存第一个（最新的）
            if video_id not in video_times:
                video_times[video_id] = watch_time
        
        processed_ids.add(video_id)
    
    # 去重并保持顺序
    unique_ids = list(OrderedDict.fromkeys(
        re.findall(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', html_content)
    ))
    
    print(f"  Unique videos: {len(unique_ids):,}")
    print(f"  Videos with time: {len(video_times):,}")
    
    # 创建 (video_id, watch_time) 列表
    video_list = []
    for vid in unique_ids:
        wtime = video_times.get(vid, 'Unknown')
        video_list.append((vid, wtime))
    
    return unique_ids, video_times

# =============================================================================
# Step 4: 调用API获取视频详情
# =============================================================================

def fetch_video_details(youtube, video_ids: list, batch_size: int = 50):
    """批量获取视频详细信息"""
    print("\n" + "="*60)
    print("Step 3: Fetching Video Details via API")
    print("="*60)
    
    if not video_ids:
        print("No video IDs to query")
        return []
    
    print(f"\nTotal videos: {len(video_ids):,}")
    print(f"Batch size: {batch_size}")
    print(f"Estimated API requests: {len(video_ids) / batch_size:.0f}")
    print(f"Estimated quota: ~{len(video_ids)} units")
    
    all_results = []
    failed_count = 0
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(video_ids) + batch_size - 1) // batch_size
        
        print(f"\nBatch {batch_num}/{total_batches}: Processing {len(batch)} videos...")
        
        try:
            response = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(batch)
            ).execute()
            
            items = response.get('items', [])
            failed_in_batch = len(batch) - len(items)
            failed_count += failed_in_batch
            
            for item in items:
                snippet = item['snippet']
                stats = item.get('statistics', {})
                
                video_info = {
                    'video_id': item['id'],
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'tags': snippet.get('tags', []),
                    'category_id': snippet.get('categoryId', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'channel_id': snippet.get('channelId', ''),
                    'view_count': stats.get('viewCount', '0'),
                    'like_count': stats.get('likeCount', '0'),
                }
                all_results.append(video_info)
            
            success_rate = len(items) / len(batch) * 100
            print(f"  Success {len(items)}/{len(batch)} ({success_rate:.0f}%)")
            
            # Avoid API limits
            if i + batch_size < len(video_ids):
                time.sleep(0.3)
                
        except Exception as e:
            print(f"  Batch error: {e}")
            failed_count += len(batch)
            continue
    
    print(f"\n{'='*60}")
    print(f"Successfully fetched {len(all_results):,} / {len(video_ids):,} videos")
    print(f"Failed: {failed_count}")
    
    return all_results

# =============================================================================
# Step 5: 转换为指定格式的字典（含观看时间）
# =============================================================================

def format_as_dict(video_details: list, video_times: dict):
    """
    转换为指定格式: 
    {
        视频名: [
            观看时间,     # 索引0 - 新增！
            ID,
            tags,
            频道,
            详情
        ]
    }
    """
    print("\n" + "="*60)
    print("Step 4: Formatting as Dictionary (with watch time)")
    print("="*60)
    
    result_dict = {}
    
    for video in video_details:
        title = video.get('title', 'Unknown')
        video_id = video.get('video_id', '')
        
        # 获取观看时间（从video_times字典中获取）
        watch_time = video_times.get(video_id, 'Unknown')
        
        tags = video.get('tags', [])
        tags_str = ', '.join(tags[:10]) if tags else ''
        
        description = video.get('description', '')
        if len(description) > 500:
            description = description[:500] + '...'
        
        # 现在列表结构：第一位是观看时间
        info = [
            watch_time,                              # 索引0: 观看时间
            video.get('video_id', ''),               # 索引1: ID
            tags_str,                                # 索引2: Tags
            video.get('channel_title', ''),          # 索引3: 频道
            description                              # 索引4: 详情
        ]
        
        result_dict[title] = info
    
    print(f"Converted {len(result_dict):,} videos")
    
    return result_dict

# =============================================================================
# 保存结果
# =============================================================================

def save_results(output_dir: Path, video_details: list, result_dict: dict, video_times: dict):
    """保存结果到文件"""
    print("\n" + "="*60)
    print("Step 5: Saving Results")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存观看时间映射（原始数据）
    times_path = output_dir / f"video_times_{timestamp}.json"
    with open(times_path, 'w', encoding='utf-8') as f:
        json.dump(video_times, f, ensure_ascii=False, indent=2)
    print(f"Watch times saved: {times_path.name}")
    
    # 保存完整详情
    details_path = output_dir / f"video_details_{timestamp}.json"
    with open(details_path, 'w', encoding='utf-8') as f:
        json.dump(video_details, f, ensure_ascii=False, indent=2)
    print(f"Details saved: {details_path.name}")
    
    # 保存字典格式
    dict_path = output_dir / f"video_dict_{timestamp}.json"
    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    print(f"Dictionary saved: {dict_path.name}")
    
    # 保存元信息
    meta = {
        "run_time": timestamp,
        "total_videos": len(video_details),
        "total_unique_videos": len(result_dict),
        "videos_with_time": len(video_times),
        "output_dir": str(output_dir)
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Metadata saved: {meta_path.name}")
    
    return times_path, details_path, dict_path, meta_path

# =============================================================================
# 打印摘要
# =============================================================================

def print_summary(result_dict: dict, video_details: list):
    """打印结果摘要"""
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    print(f"\nTotal videos processed: {len(result_dict):,}")
    
    # 统计Tag频率
    tag_counter = {}
    category_counter = {}
    
    for video in video_details:
        for tag in video.get('tags', [])[:5]:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        
        cat_id = video.get('category_id', '')
        if cat_id:
            category_counter[cat_id] = category_counter.get(cat_id, 0) + 1
    
    print("\nTop 10 Tags:")
    for tag, count in sorted(tag_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"  {tag}: {count}")
    
    print("\nTop 10 Categories:")
    for cat, count in sorted(category_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat}: {count}")
    
    # 示例输出
    print("\n" + "="*60)
    print("Sample Output (first 3 videos):")
    print("="*60)
    
    for i, (title, info) in enumerate(list(result_dict.items())[:3]):
        print(f"\n[{i+1}] {title}")
        print(f"    Watch time: {info[0]}")  # 第一位是观看时间
        print(f"    ID: {info[1]}")
        print(f"    Tags: {info[2][:80]}...")
        print(f"    Channel: {info[3]}")
        print(f"    Description: {info[4][:100]}...")

# =============================================================================
# 主函数
# =============================================================================

def main():
    print("\n" + "="*60)
    print("YouTube Takeout Data Processor")
    print("="*60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 加载配置
    config = load_config()
    if not config:
        return
    
    # 2. 设置代理
    setup_proxy(config['api']['proxy'])
    
    # 3. 初始化API
    from googleapiclient.discovery import build
    youtube = init_youtube_api(config['api']['key'])
    
    # 4. 设置路径
    base_dir = Path(config['paths']['takeout_dir'])
    takeout_dir = base_dir
    
    # 如果路径指向包含ZIP的文件夹，找实际的Takeout文件夹
    if not (takeout_dir / "YouTube 和 YouTube Music").exists():
        for subdir in takeout_dir.iterdir():
            if subdir.is_dir() and ("YouTube" in subdir.name):
                takeout_dir = subdir
                break
    
    # 5. 创建输出文件夹
    output_dir = create_output_folder(base_dir)
    
    # 6. 解压ZIP（如果需要）
    if not extract_zip_if_needed(takeout_dir):
        return
    
    # 7. 查找观看记录文件
    history_file = find_watch_history_file(takeout_dir)
    if not history_file:
        print("Watch history HTML file not found!")
        return
    
    # 8. 提取URL和观看时间
    video_ids, video_times = extract_video_urls_with_time(history_file)
    if not video_ids:
        print("No video URLs found!")
        return
    
    # 9. 获取详情
    video_details = fetch_video_details(youtube, video_ids)
    if not video_details:
        print("Failed to get video details!")
        return
    
    # 10. 转换为字典（包含观看时间）
    result_dict = format_as_dict(video_details, video_times)
    
    # 11. 保存结果
    save_results(output_dir, video_details, result_dict, video_times)
    
    # 12. 打印摘要
    print_summary(result_dict, video_details)
    
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    
    return result_dict, video_times

if __name__ == '__main__':
    main()
