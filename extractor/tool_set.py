#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 10/23/19
# IDE: PyCharm


from aioVextractor.utils.requests_retry import RequestRetry
from aioVextractor.utils.user_agent import UserAgent
from random import choice
import asyncio
import aiohttp
import platform
from aioVextractor import config
import wrapt
import re
from os.path import splitext
import html
from urllib.parse import (
    urlparse,
    parse_qs,
)

@wrapt.decorator
async def validate(func, extractor_instace, args, kwargs):
    """
    1. ensure the accuracy of the input url: match the url by `target_website` in BaseExtractor
    2. ensure the integrated of the output data according to the config.FIELDS
    :return:
    """
    ## list of regexs for matching exact webpage_url for extractor_instance
    target_website = extractor_instace.target_website
    webpage_url = kwargs['webpage_url']
    urls = []
    ## match url form webpage_url
    for regex in target_website:
        urls += re.findall(regex, webpage_url)

    ## asyncio gather these urls
    gather_results = await asyncio.gather(
        *[
            func(*args, **{**kwargs, **{"webpage_url": webpage_url}}) for webpage_url in urls
        ])

    outputs = []
    for results in gather_results:
        ## if the results is []/False/None/0
        ## skip to the next one
        if results:
            pass
        else:
            continue
            # return None

        if isinstance(results, list):
            pass
        elif isinstance(results, dict):
            results = [results]

        vid_filter = set()
        ## validate the integrity of the output
        for result in results:
            ## filter by `vid`
            try:
                vid = result['vid']
                if vid in vid_filter:
                    continue
                else:
                    vid_filter.add(result['vid'])
            except:
                # print(f"You should have specify field `vid`")
                return f"You should have specify field `vid`"

            output = dict()
            for field in config.FIELDS:
                field_info = config.FIELDS[field]
                signi_level = field_info["signi_level"]
                if signi_level == config.FIELD_SIGNI_LEVEL["else"]:
                    output[field] = result.get(field, field_info["default_value"])
                elif signi_level == config.FIELD_SIGNI_LEVEL["must"]:
                    try:
                        output[field] = result[field]
                    except KeyError:
                        print(f"You should have specify field `{field}`")
                        output = False
                        break
                elif signi_level == config.FIELD_SIGNI_LEVEL["condition_must"]:
                    dependent_field_name = field_info["dependent_field_name"]
                    dependent_field_value = field_info["dependent_field_value"]
                    dependent_field_value_actual = result.get(dependent_field_name,
                                                              "f79e2450e6b911e99af648d705c16021")
                    ## actual value of the dependent_field
                    ## if the dependent_field is not given
                    ## the default value is considered
                    dependent_field_value_actual = config.FIELDS[dependent_field_name]["default_value"] \
                        if dependent_field_value_actual == "f79e2450e6b911e99af648d705c16021" \
                        else dependent_field_value_actual
                    if dependent_field_value_actual == dependent_field_value:
                        try:
                            output[field] = result[field]
                        except KeyError:
                            print(f"You should have specify field `{field}` "
                                  f"while field `{dependent_field_name}` == {dependent_field_value}")
                            output = False
                            break
                    else:
                        ## SIGNI_LEVEL=0
                        output[field] = result.get(field, field_info['default_value'])
            if output:  ## after scanning all the listed field in config.FIELDS
                outputs.append(output)
    else:
        return outputs


class ToolSet:
    """
    Providing the most basic tools

    When you define a new extractor base on this class
    1. specify target_website as class variable
    2. inherit BaseExtractor.__init__() and define self.from_
    3. redefine BaseExtractor.entracne()
    """
    ## a list of regexs to match the target website
    ## this is used to identify whether a incoming url is extractable
    target_website = [
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),#]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
    ]

    def __init__(self, *args, **kwargs):
        self.from_ = "generic"

    @classmethod
    def suitable(cls, url):
        """
        Define a classmethod to confirm that the incoming urls
        match the regex in target_website,
        before you need to instantiate the class
        """
        urls = []
        for _VALID_URL in cls.target_website:
            urls += re.findall(_VALID_URL, url)
        else:
            return urls if urls else False

    def __enter__(self):
        ## a random headers with UA parm
        self.general_headers = lambda user_agent: {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;'
                      'v=b3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7',
        }
        self.random_ua = lambda: choice(UserAgent)
        # self.results = []
        return self

    @validate
    @RequestRetry
    async def entrance(self, webpage_url, session):
        """

        If you want to add a new extractor for a specific website,
        this is the top level API you are looking for.

        This API will not show you how to deintegrate(request and scrubbing) a website,
        but give you some convinence apis(self.extract_iframe(), @validate, @RequestRetry) and tools(self.general_headers())
        Should return necessary field
        :param webpage_url:
        :param session: aiohttp.ClientSession()
        :return:
        """
        pass

    def sync_entrance(self, webpage_url):
        """
        A synchronous entrance to call self.entrance()
        :param webpage_url:
        :return:
        """

        async def wrapper():
            async with aiohttp.ClientSession() as session:
                return await self.entrance(webpage_url=webpage_url, session=session)

        python_version = float(".".join(platform.python_version_tuple()[0:2]))
        if python_version >= 3.7:
            return asyncio.run(wrapper())
        elif 3.5 <= python_version <= 3.6:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(wrapper())
            loop.close()
            return results
        else:
            return "The Python Interpreter you are using is {python_version}.\n" \
                   "You should consider switching it to some more modern one such as Python 3.7+ " \
                .format(python_version=python_version)

    @staticmethod
    def janitor(string):
        """
        match the url(s) from string
        :param string:
        :return:
        """
        url_list = re.findall(config.URL_REGEX, string)  ## find all url in the string
        return url_list

    @staticmethod
    def check_cover(cover):
        """
        Some of the vimeo cover urls contain play_icon
        This method try to extract the url that not
        :param cover:
        :return:
        """
        if urlparse(cover).path == '/filter/overlay':
            try:
                cover_ = parse_qs(urlparse(cover).query).get('src0')[0]
            except IndexError:
                return cover
            if 'play_icon' in cover_:
                return cover
            elif cover_ is None:
                return cover
            else:
                return cover_
        else:
            return cover

    @staticmethod
    def merge_dicts(*dict_args):
        """
        Given any number of dicts, shallow copy and merge into a new dict,

        You may use new_dict = {**dict_num_one, **dict_num_two},
        which will merge dict_num_one and dict_num_two,
        and dict_num_two's value will replace dict_num_one's value when they have the same key

        This method provide something more the the above method:
        1. merging more than 2 dictionaries
        2. only replace the previous value with the upcoming value if the previous value is in {None/False/0}
        """

        result = {}
        for dictionary in dict_args:
            for k, v in dictionary.items():
                if k in result:
                    result[k] = result[k] if result[k] else v
                else:
                    result[k] = v
            result.update(dictionary)
        return result

    @RequestRetry
    async def retrieve_webpapge(self, webpage_url):
        """
        retrieve webpage
        """
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.get(webpage_url, headers=self.general_headers(self.random_ua())) as response:
                return await response.text()

    @staticmethod
    def unescape(string):
        if string:
            return html.unescape(string)
        else:
            return None

    @staticmethod
    def get_ext(url_):
        """
        Return the filename extension from url, or ''
        """
        if url_ is None:
            return False
        parsed = urlparse(url_)
        root, ext_ = splitext(parsed.path)
        ext = ext_[1:]  # or ext[1:] if you don't want the leading '.'
        ## ext = 'jpeg@80w_80h_1e_1c'
        return ext.split('@')[0]

    @RequestRetry
    async def request_get(self, url, session, response_type="text", **kwargs):
        async with session.get(url, **kwargs) as response:
            if response_type == "text":
                return await response.text()
            elif response_type == "json":
                return await response.json()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # asyncio.run(self.async_session.close())
        print(f"exc_type, exc_val, exc_tb: {exc_type, exc_val, exc_tb}")
