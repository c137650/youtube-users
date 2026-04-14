# -*- coding: utf-8 -*-
"""
YouTube API 调用脚本 - 使用代理
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json

# 设置代理
os.environ['HTTP_PROXY'] = 'http://proxy-dku.oit.duke.edu:3128'
os.environ['HTTPS_PROXY'] = 'http://proxy-dku.oit.duke.edu:3128'
os.environ['http_proxy'] = 'http://proxy-dku.oit.duke.edu:3128'
os.environ['https_proxy'] = 'http://proxy-dku.oit.duke.edu:3128'

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# API配置
API_KEY = 'AIzaSyCfqxUG56YJYfg3RzXPbGAqiNWUXPTuecI'
youtube = build('youtube', 'v3', developerKey=API_KEY)

def test_api():
    """测试API连接"""
    try:
        print('Testing YouTube API...')
        response = youtube.channels().list(
            part='snippet,statistics',
            id='UC_x5XG1OV2P6uZZ5FSM9Ttw'  # Google Developers
        ).execute()
        
        if response['items']:
            channel = response['items'][0]
            print('API OK!')
            print(f"Channel: {channel['snippet']['title']}")
            print(f"Subscribers: {channel['statistics']['subscriberCount']}")
            return True
    except Exception as e:
        print(f"API Error: {e}")
        return False

def get_video_details(video_id):
    """获取单个视频详细信息"""
    try:
        response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        
        if response['items']:
            video = response['items'][0]['snippet']
            details = {
                'video_id': video_id,
                'title': video.get('title', ''),
                'description': video.get('description', ''),
                'tags': video.get('tags', []),
                'category_id': video.get('categoryId', ''),
                'published_at': video.get('publishedAt', ''),
                'channel_title': video.get('channelTitle', ''),
            }
            return details
    except Exception as e:
        print(f"Get video {video_id} failed: {e}")
        return None

def get_batch_videos(video_ids):
    """批量获取视频信息"""
    results = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            response = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(batch)
            ).execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                results.append({
                    'video_id': item['id'],
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'tags': snippet.get('tags', []),
                    'category_id': snippet.get('categoryId', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'has_caption': item['contentDetails'].get('caption', 'false'),
                })
        except Exception as e:
            print(f"Batch {i//50} error: {e}")
    
    return results

if __name__ == '__main__':
    print('=' * 50)
    print('YouTube API via Duke Proxy')
    print('Proxy: proxy-dku.oit.duke.edu:3128')
    print('=' * 50)
    
    if test_api():
        print('\nTesting single video...')
        video = get_video_details('dQw4w9WgXcQ')
        if video:
            print(f"\nVideo: {video['title']}")
            print(f"Channel: {video['channel_title']}")
            print(f"Tags: {video['tags'][:5] if video['tags'] else 'None'}")
