# -*- coding: utf-8 -*-
"""
YouTube Takeout 数据处理脚本
从观看记录HTML中提取视频URL，调用API获取详情
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

# =============================================================================
# 配置加载
# =============================================================================

def load_config():
    """从config.json加载配置"""
    config_path = Path(__file__).parent / "config.json"
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n" + "="*60)
    print("配置加载成功 / Config Loaded")
    print("="*60)
    print(f"API Key: {config['api']['key'][:20]}...")
    print(f"Proxy: {config['api']['proxy']['http']}")
    print(f"Takeout路径: {config['paths']['takeout_dir']}")
    
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
    print("✅ 代理已设置")

# =============================================================================
# YouTube API 初始化
# =============================================================================

def init_youtube_api(api_key):
    """初始化YouTube API"""
    from googleapiclient.discovery import build
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    print("✅ YouTube API 已初始化")
    
    return youtube

# =============================================================================
# Step 1: 创建输出文件夹
# =============================================================================

def create_output_folder(base_dir: Path):
    """创建输出文件夹，序号自动+1"""
    outcome_dir = base_dir / "outcome"
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
    
    print(f"\n📁 输出文件夹: {output_dir}")
    
    return output_dir

# =============================================================================
# Step 2: 解压ZIP文件（如果需要）
# =============================================================================

def extract_zip_if_needed(takeout_dir: Path):
    """检查并解压ZIP文件"""
    print("\n" + "="*60)
    print("Step 1: 检查并解压ZIP文件 / Checking ZIP files")
    print("="*60)
    
    # 查找ZIP文件
    zip_files = list(takeout_dir.glob("*.zip")) + list(takeout_dir.glob("*.rar"))
    
    if not zip_files:
        print("✅ 未找到ZIP文件，无需解压")
        return True
    
    for zip_path in zip_files:
        print(f"\n找到ZIP文件: {zip_path.name}")
        extract_to = takeout_dir / zip_path.stem
        
        if extract_to.exists():
            print(f"  ⚠️ 已解压，跳过: {extract_to}")
            continue
        
        print(f"  正在解压到: {extract_to}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(takeout_dir)
            print("  ✅ 解压完成!")
        except Exception as e:
            print(f"  ❌ 解压失败: {e}")
            return False
    
    return True

# =============================================================================
# Step 3: 提取视频URL
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

def extract_video_urls(history_file: Path):
    """从HTML文件中提取YouTube视频URL"""
    print("\n" + "="*60)
    print("Step 2: 从HTML中提取视频URL / Extracting Video URLs")
    print("="*60)
    
    print(f"\n📂 读取文件: {history_file}")
    
    # 读取HTML内容
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        try:
            with open(history_file, 'r', encoding='latin-1') as f:
                html_content = f.read()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return []
    
    print(f"  文件大小: {len(html_content):,} bytes")
    
    # 提取YouTube视频URL
    url_pattern = r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
    video_ids = re.findall(url_pattern, html_content)
    
    # 去重并保持顺序
    unique_ids = list(dict.fromkeys(video_ids))
    
    print(f"  找到 {len(video_ids):,} 个URL（含重复）")
    print(f"  去重后: {len(unique_ids):,} 个唯一视频")
    
    return unique_ids

# =============================================================================
# Step 4: 调用API获取视频详情
# =============================================================================

def fetch_video_details(youtube, video_ids: list, batch_size: int = 50):
    """批量获取视频详细信息"""
    print("\n" + "="*60)
    print("Step 3: 调用API获取视频详情 / Fetching Video Details")
    print("="*60)
    
    if not video_ids:
        print("❌ 没有视频ID可查询")
        return []
    
    print(f"\n📊 总共 {len(video_ids):,} 个视频")
    print(f"📦 批次大小: {batch_size}")
    print(f"🔢 预计需要 {len(video_ids) / batch_size:.0f} 个API请求")
    print(f"💰 预计配额消耗: ~{len(video_ids)} 单位")
    
    all_results = []
    failed_count = 0
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(video_ids) + batch_size - 1) // batch_size
        
        print(f"\n批次 {batch_num}/{total_batches}: 处理 {len(batch)} 个视频...")
        
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
            print(f"  ✅ 成功 {len(items)}/{len(batch)} ({success_rate:.0f}%)")
            
            # 避免API限制
            if i + batch_size < len(video_ids):
                time.sleep(0.3)
                
        except Exception as e:
            print(f"  ❌ 批次错误: {e}")
            failed_count += len(batch)
            continue
    
    print(f"\n{'='*60}")
    print(f"✅ 成功获取 {len(all_results):,} / {len(video_ids):,} 个视频详情")
    print(f"❌ 失败: {failed_count} 个")
    
    return all_results

# =============================================================================
# Step 5: 转换为指定格式的字典
# =============================================================================

def format_as_dict(video_details: list):
    """转换为指定格式: {视频名: [ID, tags, 频道, 详情]}"""
    print("\n" + "="*60)
    print("Step 4: 转换为字典格式 / Formatting as Dictionary")
    print("="*60)
    
    result_dict = {}
    
    for video in video_details:
        title = video.get('title', 'Unknown')
        tags = video.get('tags', [])
        tags_str = ', '.join(tags[:10]) if tags else ''
        
        description = video.get('description', '')
        if len(description) > 500:
            description = description[:500] + '...'
        
        info = [
            video.get('video_id', ''),
            tags_str,
            video.get('channel_title', ''),
            description
        ]
        
        result_dict[title] = info
    
    print(f"✅ 转换完成: {len(result_dict):,} 个视频")
    
    return result_dict

# =============================================================================
# 保存结果
# =============================================================================

def save_results(output_dir: Path, video_details: list, result_dict: dict):
    """保存结果到文件"""
    print("\n" + "="*60)
    print("Step 5: 保存结果 / Saving Results")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整详情
    details_path = output_dir / f"video_details_{timestamp}.json"
    with open(details_path, 'w', encoding='utf-8') as f:
        json.dump(video_details, f, ensure_ascii=False, indent=2)
    print(f"✅ 详情已保存: {details_path.name}")
    
    # 保存字典格式
    dict_path = output_dir / f"video_dict_{timestamp}.json"
    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    print(f"✅ 字典已保存: {dict_path.name}")
    
    # 保存元信息
    meta = {
        "run_time": timestamp,
        "total_videos": len(video_details),
        "total_unique_videos": len(result_dict),
        "output_dir": str(output_dir)
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"✅ 元信息已保存: {meta_path.name}")
    
    return details_path, dict_path, meta_path

# =============================================================================
# 打印摘要
# =============================================================================

def print_summary(result_dict: dict, video_details: list):
    """打印结果摘要"""
    print("\n" + "="*60)
    print("📊 结果摘要 / Summary")
    print("="*60)
    
    print(f"\n总共处理 {len(result_dict):,} 个视频")
    
    # 统计Tag频率
    tag_counter = {}
    category_counter = {}
    
    for video in video_details:
        for tag in video.get('tags', [])[:5]:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        
        cat_id = video.get('category_id', '')
        if cat_id:
            category_counter[cat_id] = category_counter.get(cat_id, 0) + 1
    
    print("\n🏷️ Top 10 Tags:")
    for tag, count in sorted(tag_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"  {tag}: {count}")
    
    print("\n📁 Top 10 Categories:")
    for cat, count in sorted(category_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat}: {count}")
    
    # 示例输出
    print("\n" + "="*60)
    print("📝 示例输出 (前3个视频):")
    print("="*60)
    
    for i, (title, info) in enumerate(list(result_dict.items())[:3]):
        print(f"\n【{i+1}】{title}")
        print(f"    ID: {info[0]}")
        print(f"    Tags: {info[1][:80]}...")
        print(f"    频道: {info[2]}")
        print(f"    详情: {info[3][:100]}...")

# =============================================================================
# 主函数
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🚀 YouTube Takeout 数据处理")
    print("    YouTube Takeout Data Processor")
    print("="*60)
    print(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        print("❌ 未找到观看记录HTML文件!")
        return
    
    # 8. 提取URL
    video_ids = extract_video_urls(history_file)
    if not video_ids:
        print("❌ 未找到视频URL!")
        return
    
    # 9. 获取详情
    video_details = fetch_video_details(youtube, video_ids)
    if not video_details:
        print("❌ 未能获取视频详情!")
        return
    
    # 10. 转换为字典
    result_dict = format_as_dict(video_details)
    
    # 11. 保存结果
    save_results(output_dir, video_details, result_dict)
    
    # 12. 打印摘要
    print_summary(result_dict, video_details)
    
    print("\n" + "="*60)
    print("✅ 处理完成! / Processing Complete!")
    print("="*60)
    
    return result_dict

if __name__ == '__main__':
    main()
