#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 2019/6/20
# IDE: PyCharm

from aioVextractor.utils.requests_retry import RequestRetry
from bs4 import BeautifulSoup
import re, json, time
import traceback


async def entrance(webpage_url, session):
    video = await extract_video_info(webpage_url, session=session)
    return video


@RequestRetry
async def extract_video_info(webpage_url, session):
    async with session.get(webpage_url) as resp:
        item = dict()
        text = await resp.text()
        soup = BeautifulSoup(text, 'lxml')
        video = soup.find("video", attrs={"id": "recipe-media"})
        item['from'] = "懒饭"
        item['duration'] = 0
        item['webpage_url'] = webpage_url
        item['cover'] = video.get("poster")
        item['play_addr'] = video.get("src")
        item['width'] = video.get("width")
        item['height'] = video.get("height")
        h1 = soup.find("h1", attrs={"class": "recipe-name title-1"})
        if h1:
            item['title'] = h1.text
        font = soup.find("div", attrs={'class': "recipe-meta-item score"})
        if font:
            try:
                score = font.text.strip().replace("评分", "").strip()
                item['rating'] = score
            except:
                pass
        jsonstr = re.findall("window.__NUXT__=(.*?);<", text)
        if jsonstr:
            try:
                jsondata = json.loads(jsonstr[0])['data'][0]['recipe']
                item['collect_count'] = jsondata['n_collects']
                item['comment_count'] = jsondata['n_comments']
                item['vid'] = jsondata.get('id')
                item['description'] = jsondata.get('desc')
                try:
                    item['upload_ts'] = jsondata.get("create_time")
                    item['upload_ts'] = int(time.mktime(time.strptime(item['upload_ts'], "%Y-%m-%d %H:%M:%S")))
                except:
                    traceback.print_exc()
            except:
                traceback.print_exc()
        return item


TEST_CASE = [
    "https://lanfanapp.com/recipe/3127/",
]

if __name__ == '__main__':
    import asyncio
    import aiohttp
    from pprint import pprint


    async def test():
        async with aiohttp.ClientSession() as session_:
            return await entrance("https://lanfanapp.com/recipe/278/", session_)


    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(test())
    pprint(res)