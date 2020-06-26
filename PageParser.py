from bs4 import BeautifulSoup as bs
import requests
import urllib
import concurrent.futures
import time
import re
import random
import os
import asyncio
import aiohttp
import aiofiles

from typing import List


class wikiPerson:
    # static variable so that urls aren't repeated
    urls = []
    img_urls = []
    img_names = []
    sentences = []

    def __init__(self, url, height):
        self.url = url
        self.name = None
        self.img_path = None
        self.intro_sentence = None
        self.children = []
        self.img_urls = []
        self.__class__.urls.append(self.url)

        if height:
            self.set_child_vars(height)

            # downloads asynchronously to speed up run time
            self.download_all()

    def download_all(self):
       for i in range(len(self.__class__.img_urls)):
           self.download_image(self.__class__.img_urls[i], self.__class__.img_names[i])

    def download_image(self, url, name):
        # download the thumbnail image
        img = requests.get(url).content
        with open(name, 'wb') as img_file:
            img_file.write(img)

    def set_child_vars(self, height):
        if height >= 0:
            self.set_vars(height == 0)
            for child in self.children:
                child.set_child_vars(height - 1)

    def set_vars(self, is_leaf):
        res = requests.get(self.url)
        soup = bs(res.content, 'lxml')

        children = []

        # only includes people who have articles with first and last names
        # i.e. the musician "Prince" would NOT be included

        # set the name
        self.name = soup.title.string.split("-")[0][:-1]

        # set the image link
        table = soup.find('table', class_='infobox biography vcard')

        if not table:
            table = soup.find('table', class_='infobox vcard')

        # safe operation since we checked that an image exists when creating the Person object
        img = table.find("img")
        img_link = "http:" + img.get("src")
        self.__class__.img_urls.append(img_link)

        # images are stored in images folder in cwd
        self.img_path = os.path.abspath(os.path.join(os.getcwd(), "images", self.name.replace(" ", "_") + ".GIF"))
        self.__class__.img_names.append(self.img_path)

        if not is_leaf:
            # set the child links
            # put the links through a "soft filter" i.e. checking if link title fits format of name
            # then through a "hard filter", i.e. checking if it contains a biography tag in the html
            soup_links = soup.find("div", {"id": "bodyContent"}).find_all("a")
            possible_names = []
            i = 0

            for link in soup_links:
                new = link.get("href", "")
                curr_url = "https://en.wikipedia.org" + new

                # ensure person hasn't already been added
                if wikiPerson.is_name_link(new) and (curr_url not in self.__class__.urls):
                    possible_names.append(new)

            people_added = 0
            i = 0

            paragraphs = soup.select("p")

            while i < len(possible_names) and people_added < 2:
                    res = wikiPerson.is_person(possible_names[i])
                    if res:
                        new_person = wikiPerson("https://en.wikipedia.org" + possible_names[i], 0)
                        tmp_name = possible_names[i][6:].split("_")
                        name = tmp_name[0] + " " + tmp_name[1]
                        new_person.intro_sentence = wikiPerson.get_sentence(paragraphs, name)
                        children.append(new_person)
                        people_added += 1
                    i += 1

            self.children = children

    def get_path(self):
        return self.img_path

    def get_name(self):
        return self.name

    def get_intro(self):
        return self.intro_sentence

    @staticmethod
    def get_sentence(paragraphs, name):
        for para in paragraphs:
            if name in para.text:
                sentences = para.text.split(".")
                for sentence in sentences:
                    if name in sentence:
                        return sentence + "."

    def get_bfs_paths(self):
        '''
        :return: a 3-tuple of containing 3 lists, one containing paths, one containing sentences and the other containing names
         of the images stored in tree in BFS order
        '''
        paths = []
        names = []
        intro_sents = []

        # start with root node
        queue = [self]
        while queue:
            curr_node = queue.pop(0)
            paths.append(curr_node.get_path())
            names.append(curr_node.get_name())
            intro_sents.append(curr_node.get_intro())
            queue.extend(curr_node.children)

        return tuple([paths, intro_sents[1:], names])

    @staticmethod
    def is_person(new):
        """
        :param new: a wikipedia url that starts with /wiki/
        :return: returns whether is a link to a wikipedia page about a person
        """
        if new.startswith("/wiki/"):
            is_person = False
            new_url = "https://en.wikipedia.org" + new
            new_soup = bs(requests.get(new_url).text, 'lxml')
            # only articles about people have the 'infobox biography vcard tag';
            # this distinguishes from other articles that match the regex
            # less notable people won't have the tag either
            table = new_soup.find('table')

            if not table:
                return False

            rows = table.find_all('tr')
            has_img = table.find('img') is not None

            for row in rows:
                curr = row.find('th')
                # 'born' header only for articles about people
                if curr and 'Born' in curr.text:
                    is_person = True

            if is_person and has_img:
                return True
            return False

    @staticmethod
    def is_name_link(new):
        """
        :param new: A wikipedia url that starts with /wiki/
        :return: returns true if url contains two words and both words contain capital letters
        """
        parsed_link = new[6:].split("_")
        return len(parsed_link) == 2 and all(re.search("^[A-Z]", elem) for elem in parsed_link)
