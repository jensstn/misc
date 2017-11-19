#!/usr/bin/python3

import argparse
import base64
import getpass
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# https://app.scrumdo.com/api/v3/docs

base_url = "https://app.scrumdo.com/api/v3/"
default_config_path = os.path.join(os.getenv("HOME"), ".scrumdorc")

points = ["?", "0", "0.5", "1", "2", "3", "5", "8", "13", "20", "40", "100",
    "Infinite"]

class ScrumdoObject(object):
    def __init__(self, name, slug, _id):
        self.name = name
        self.slug = slug
        self._id = _id

class IterationObject(ScrumdoObject):
    def __init__(self, name, url, _id):
        ScrumdoObject.__init__(self, name, None, _id)
        self.url = url

class ScrumdoStory(object):
    def __init__(self, story_json):
        self.name = make_story_name(story_json["prefix"],
            story_json["number"])
        self.summary = get_strings(story_json["summary"])
        self.details = get_strings(story_json["detail"])
        self.accept_criteria = get_strings(story_json["extra_1"])
        self.note = get_strings(story_json["extra_3"])
        self.permalink = "https://app.scrumdo.com/projects/story_permalink/{}"\
            .format(story_json["id"])
        self.tags = get_strings(story_json["tags"])
        self.labels = "".join(get_strings(l["name"]) for l
            in story_json["labels"])

    def print_story(self):
        print("""{}: {}

Details:
\t{}

Accept criteria:
\t{}

Note:
\t{}

Tags:
\t{}

Labels:
\t{}

[Permalink: {}]""".format(self.name, self.summary, self.details,
            self.accept_criteria, self.note, self.tags, self.labels,
            self.permalink))

class ScrumdoContext(object):
    def __init__(self, auth, organization, project):
        self.auth = auth
        self.organization = organization
        self.project = project

    def open_page(self, url, data=None):
        # http basic auth
        # https://en.wikipedia.org/wiki/Basic_access_authentication
        # https://tools.ietf.org/html/rfc2617
        headers = {"Authorization":
            "Basic {}".format(self.auth)}
        req = urllib.request.Request(url, data, headers)
        p = urllib.request.urlopen(req)
        return p.read().decode("utf8")

    def get_stories(self):
        t = self.open_page("{}/organizations/{}/projects/{}/stories/".format(
            base_url, self.organisation, self.project))
        return json.loads(t)

    def search_stories(self, query):
        data = urllib.parse.urlencode({"q": query})
        t = self.open_page("{}/organizations/{}/projects/{}/search?{}".format(
            base_url, self.organization, self.project, data))
        return json.loads(t)

    def search_for_name(self, story_name):
        parts = re.search("([a-zA-Z]+)?-?(\d+)", story_name)
        if parts is None:
            print("unknown story id format: {}".format(sys.argv[1]),
                file=sys.stderr)
            sys.exit(1)
        prefix = parts.groups()[0]
        number = parts.groups()[1]
        story_id = self.find_story(int(number), prefix)
        if story_id != -1:
            return self.get_story(story_id)
        return None

    def get_story(self, story_id):
        t = self.open_page("{}/organizations/{}/projects/{}/stories/{}".format(
            base_url, self.organization, self.project, str(story_id)))
        return json.loads(t)

    def find_story(self, number, prefix=None):
        story_name = make_story_name(prefix, number)
        stories = self.search_stories(story_name)
        # TODO: hvad hvis len(items) er < count
        for story in stories["items"]:
            if prefix is not None and prefix != story["prefix"]:
                continue
            if story["number"] == number:
                return story["id"]
        return -1

    def get_iterations(self):
        t = self.open_page("{}/organizations/{}/projects/{}/iterations".format(
            base_url, self.organization, self.project))
        iterations = []
        for it in json.loads(t):
            obj = IterationObject(it["name"], it["url"], it["id"])
            iterations.append(obj)
        return iterations

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("story_name")
    parser.add_argument("--auth", help="user name and password for "
        "scrumdo in the format username:password encoded as base64")
    parser.add_argument("-o", "--organization", default="dbc")
    parser.add_argument("-p", "--project", default="data-indud")
    parser.add_argument("--config-file", default=default_config_path)
    return parser.parse_args()

def get_strings(xml_string):
    if xml_string == "":
        return ""
    xml_string = html.unescape(xml_string)
    xml_string = "<wrapper>" + xml_string + "</wrapper>"
    root = ET.fromstring(xml_string)
    children = [root]
    s = ""
    while children:
        child = children.pop()
        if child.text is not None:
            s += child.text + "\n"
        children += reversed(child.getchildren())
    return break_string(s)

def break_string(s):
    s = s.replace("\n", " $$$ ")
    tokens = [w for w in re.split("\s", s)]
    mean = 0
    s_out = ""
    for t in tokens:
        if mean > 72 or t == "$$$":
            s_out += "\n\t"
            mean = 0
        if t != "$$$":
            s_out += t + " "
            mean += len(t)
    return s_out.strip()

def print_story(story_json):
    story = ScrumdoStory(story_json)
    story.print_story()

def make_story_name(prefix, number):
    if prefix is None or prefix == "":
        return str(number)
    else:
        return prefix + "-" + str(number)

def read_config(config_path):
    if os.path.exists(config_path):
        config = {}
        with open(config_path) as f:
            for line in f:
                r = re.search("(\w+)\s*:\s*(.*)", line)
                if r is None:
                    continue
                key, value = r.groups()
                config[key] = value
        return config
    return None

def get_auth(args, config):
    if args.auth is None and config is not None and "auth" in config:
        return config["auth"]
    elif args.auth is not None:
        return args.auth
    else:
        user = input("scrumdo username: ")
        psswd = getpass.getpass("scrumdo password: ")
        auth = base64.b64encode("{}:{}".format(user, psswd).encode("utf8"))
        return auth.decode("utf8")

if __name__ == "__main__":
    args = setup_args()
    config = read_config(args.config_file)
    auth = get_auth(args, config)
    scrumdo_context = ScrumdoContext(auth, args.organization, args.project)
    story_json = scrumdo_context.search_for_name(args.story_name)
    if story_json is not None:
        print_story(story_json)
    else:
        print("no story found with name {}".format(args.story_name),
            file=sys.stderr)
        sys.exit(1)
