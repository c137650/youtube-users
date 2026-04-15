# -*- coding: utf-8 -*-
"""
YouTube 记忆图谱 - 主程序
整合数据处理和标签匹配的全流程
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
# Step 2: 解压ZIP文件
# =============================================================================

def extract_zip_if_needed(takeout_dir: Path):
    """检查并解压ZIP文件"""
    print("\n" + "="*60)
    print("Step 1: Checking ZIP files")
    print("="*60)

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
# Step 3: 查找观看记录文件
# =============================================================================

def find_watch_history_file(takeout_dir: Path):
    """查找观看记录HTML文件"""
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

    html_files = list(history_dir.glob("*.html"))

    for f in html_files:
        if "观看记录" in f.name or "watch" in f.name.lower():
            return f

    return html_files[0] if html_files else None

# =============================================================================
# Step 4: 提取视频URL和观看时间
# =============================================================================

def extract_video_urls_with_time(history_file: Path):
    """从HTML文件中提取YouTube视频URL和观看时间"""
    print("\n" + "="*60)
    print("Step 2: Extracting Video URLs and Watch Times")
    print("="*60)

    print(f"\nReading file: {history_file}")

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

    # 提取 video_id
    simple_pattern = r'watch\?v=([a-zA-Z0-9_-]{11})'
    all_matches = list(re.finditer(simple_pattern, html_content))

    print(f"  Found {len(all_matches):,} video URLs")

    # 时间模式
    time_pattern = r'([\d]{4}年[\d]+月[\d]+日)[\s]*([上下]?午[\d:]+)?'

    # 从后往前处理
    video_times = {}
    processed_ids = set()

    for match in reversed(all_matches):
        video_id = match.group(1)

        if video_id in processed_ids:
            continue

        start_pos = match.end()
        search_window = html_content[start_pos:start_pos + 200]

        time_match = re.search(time_pattern, search_window)
        if time_match:
            date_str = time_match.group(1)
            time_str = time_match.group(2) if time_match.group(2) else ""
            watch_time = f"{date_str} {time_str}".strip()

            if video_id not in video_times:
                video_times[video_id] = watch_time

        processed_ids.add(video_id)

    # 去重保持顺序
    unique_ids = list(OrderedDict.fromkeys(
        re.findall(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', html_content)
    ))

    print(f"  Unique videos: {len(unique_ids):,}")
    print(f"  Videos with time: {len(video_times):,}")

    return unique_ids, video_times

# =============================================================================
# Step 5: 调用API获取视频详情
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
# Step 6: 转换为字典格式
# =============================================================================

def format_as_dict(video_details: list, video_times: dict):
    """转换为字典格式: {视频名: [观看时间, ID, tags, 频道, 详情]}"""
    print("\n" + "="*60)
    print("Step 4: Formatting as Dictionary")
    print("="*60)

    result_dict = {}

    for video in video_details:
        title = video.get('title', 'Unknown')
        video_id = video.get('video_id', '')
        watch_time = video_times.get(video_id, 'Unknown')

        tags = video.get('tags', [])
        tags_str = ', '.join(tags[:10]) if tags else ''

        description = video.get('description', '')
        if len(description) > 500:
            description = description[:500] + '...'

        info = [
            watch_time,
            video.get('video_id', ''),
            tags_str,
            video.get('channel_title', ''),
            description
        ]

        result_dict[title] = info

    print(f"Converted {len(result_dict):,} videos")

    return result_dict

# =============================================================================
# Step 7: 加载用户标签
# =============================================================================

def load_user_tags():
    """加载用户标签配置"""
    tags_path = Path(__file__).parent / "user_tags.json"

    if not tags_path.exists():
        print("user_tags.json not found")
        return None

    with open(tags_path, 'r', encoding='utf-8') as f:
        tags_config = json.load(f)

    print("Loaded tag configuration")

    # 合并所有分类的标签
    all_tags = {}

    for category in ['core_tags', 'meme_tags', 'social_tags', 'time_tags']:
        if category in tags_config:
            for tag_name, tag_info in tags_config[category].items():
                all_tags[tag_name] = {
                    'emoji': tag_info.get('emoji', ''),
                    'keywords': tag_info.get('keywords', []),
                    'category': category
                }

    print(f"   Total tags loaded: {len(all_tags)}")

    return all_tags

# =============================================================================
# Step 8: 匹配标签
# =============================================================================

def build_pattern(keywords):
    """构建正则表达式"""
    if not keywords:
        return None
    escaped = [re.escape(k) for k in keywords]
    pattern = '|'.join(escaped)
    return re.compile(pattern, re.IGNORECASE)

def match_video(video_info, all_tags, video_times):
    """匹配单个视频的标签"""
    matched_tags = []

    title = video_info.get('title', '')
    description = video_info.get('description', '')
    api_tags = video_info.get('tags', [])
    channel = video_info.get('channel_title', '')
    video_id = video_info.get('video_id', '')

    match_text = f"{title} {description} {' '.join(api_tags)} {channel}".lower()
    url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    watch_time = video_times.get(video_id, 'Unknown')

    for tag_name, tag_config in all_tags.items():
        keywords = tag_config.get('keywords', [])
        pattern = build_pattern(keywords)

        if pattern and pattern.search(match_text):
            matched_tags.append(tag_name)

    if matched_tags:
        return [', '.join(matched_tags), url, watch_time]

    return None

def match_all_labels(video_details, video_times, all_tags):
    """匹配所有视频的标签"""
    print("\n" + "="*60)
    print("Step 5: Label Matching")
    print("="*60)

    result = {}
    tag_counter = {}

    for i, video in enumerate(video_details):
        title = video.get('title', 'Unknown')
        matched = match_video(video, all_tags, video_times)

        if matched:
            result[title] = matched

            tags_str = matched[0]
            for tag in tags_str.split(', '):
                tag_counter[tag] = tag_counter.get(tag, 0) + 1

        if (i + 1) % 100 == 0:
            print(f"   Progress: {i+1}/{len(video_details)}")

    print(f"\nMatching complete:")
    print(f"   Videos with labels: {len(result)}")
    print(f"   Tag types matched: {len(tag_counter)}")

    return result, tag_counter

# =============================================================================
# Step 9: 保存结果
# =============================================================================

def save_results(output_dir: Path, video_details: list, result_dict: dict,
                 video_times: dict, labels_dict: dict):
    """保存所有结果到文件"""
    print("\n" + "="*60)
    print("Step 6: Saving Results")
    print("="*60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存观看时间映射
    times_path = output_dir / f"video_times_{timestamp}.json"
    with open(times_path, 'w', encoding='utf-8') as f:
        json.dump(video_times, f, ensure_ascii=False, indent=2)
    print(f"Watch times saved: {times_path.name}")

    # 保存完整详情
    details_path = output_dir / f"video_details_{timestamp}.json"
    with open(details_path, 'w', encoding='utf-8') as f:
        json.dump(video_details, f, ensure_ascii=False, indent=2)
    print(f"Video details saved: {details_path.name}")

    # 保存字典格式
    dict_path = output_dir / f"video_dict_{timestamp}.json"
    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    print(f"Video dict saved: {dict_path.name}")

    # 保存标签结果
    labels_path = output_dir / f"video_labels_{timestamp}.json"
    with open(labels_path, 'w', encoding='utf-8') as f:
        json.dump(labels_dict, f, ensure_ascii=False, indent=2)
    print(f"Labels saved: {labels_path.name}")

    # 保存元信息
    meta = {
        "run_time": timestamp,
        "total_videos": len(video_details),
        "total_unique_videos": len(result_dict),
        "videos_with_labels": len(labels_dict),
        "output_dir": str(output_dir)
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Metadata saved: {meta_path.name}")

    return labels_path

# =============================================================================
# Step 10: 打印摘要
# =============================================================================

def print_summary(result_dict: dict, labels_dict: dict, tag_counter: dict):
    """打印结果摘要"""
    print("\n" + "="*60)
    print("Summary")
    print("="*60)

    print(f"\nTotal videos processed: {len(result_dict):,}")
    print(f"Videos with labels: {len(labels_dict):,}")

    print("\nTop 20 Tags:")
    sorted_tags = sorted(tag_counter.items(), key=lambda x: -x[1])[:20]
    for i, (tag, count) in enumerate(sorted_tags, 1):
        print(f"   {i:2d}. {tag}: {count}")

    print("\n" + "="*60)
    print("Sample Output:")
    print("="*60)

    items = list(labels_dict.items())[:3]
    for i, (title, info) in enumerate(items, 1):
        tags_str, url, watch_time = info
        print(f"\n[{i}] {title}")
        print(f"    Tags: {tags_str}")
        print(f"    URL: {url}")
        print(f"    Time: {watch_time}")

# =============================================================================
# 主函数
# =============================================================================

def main():
    print("\n" + "="*60)
    print("YouTube Memory Graph - Full Pipeline")
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

    if not (takeout_dir / "YouTube 和 YouTube Music").exists():
        for subdir in takeout_dir.iterdir():
            if subdir.is_dir() and ("YouTube" in subdir.name):
                takeout_dir = subdir
                break

    # 5. 创建输出文件夹
    output_dir = create_output_folder(base_dir)

    # 6. 解压ZIP
    if not extract_zip_if_needed(takeout_dir):
        return

    # 7. 查找观看记录
    history_file = find_watch_history_file(takeout_dir)
    if not history_file:
        print("Watch history HTML file not found!")
        return

    # 8. 提取URL和观看时间
    video_ids, video_times = extract_video_urls_with_time(history_file)
    if not video_ids:
        print("No video URLs found!")
        return

    # 9. 获取视频详情
    video_details = fetch_video_details(youtube, video_ids)
    if not video_details:
        print("Failed to get video details!")
        return

    # 10. 转换为字典
    result_dict = format_as_dict(video_details, video_times)

    # 11. 加载标签配置
    all_tags = load_user_tags()
    if not all_tags:
        return

    # 12. 匹配标签
    labels_dict, tag_counter = match_all_labels(video_details, video_times, all_tags)

    # 13. 保存结果
    labels_path = save_results(output_dir, video_details, result_dict,
                               video_times, labels_dict)

    # 14. 打印摘要
    print_summary(result_dict, labels_dict, tag_counter)

    print("\n" + "="*60)
    print("Pipeline Complete!")
    print(f"Output: {output_dir}")
    print("="*60)

    return labels_dict

if __name__ == '__main__':
    main()
