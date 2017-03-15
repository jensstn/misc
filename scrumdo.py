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

base_url = "https://app.scrumdo.com/api/v3/"
auth = None

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("story_name")
    parser.add_argument("--auth", help="user name and password for "
        "scrumdo in the format username:password encoded as base64")
    parser.add_argument("-o", "--organization", default="dbc")
    parser.add_argument("-p", "--project", default="data-indud")
    parser.add_argument("--config-file", default=os.path.join(
        os.getenv("HOME"), ".scrumdorc"))
    return parser.parse_args()

def open_page(url, data=None):
    # http basic auth
    # https://en.wikipedia.org/wiki/Basic_access_authentication
    # https://tools.ietf.org/html/rfc2617
    headers = {"Authorization":
        "Basic {}".format(auth)}
    req = urllib.request.Request(url, data, headers)
    p = urllib.request.urlopen(req)
    return p.read().decode("utf8")

def get_stories(organisation, project):
    t = open_page("{}/organizations/{}/projects/{}/stories/".format(base_url, organisation, project))
    return json.loads(t)

def search_stories(organisation, project, query):
    data = urllib.parse.urlencode({"q": query})
    t = open_page("{}/organizations/{}/projects/{}/search?{}".format(base_url, organisation, project, data))
    return json.loads(t)

def get_story(organisation, project, story_id):
    t = open_page("{}/organizations/{}/projects/{}/stories/{}".format(base_url, organisation, project, str(story_id)))
    return json.loads(t)

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
    name = make_story_name(story_json["prefix"], story_json["number"])
    accept_criteria = story_json["extra_1"]
    note = story_json["extra_3"]
    s = "{}: {}\n\nDetails:\n\t{}\n\nAccept criteria:\n\t{}\n\n"\
        "Note:\n\t{}\n\n[Permalink: https://app.scrumdo.com/projects/"\
        "story_permalink/{}]".format(name, get_strings(story_json["summary"]),
        get_strings(story_json["detail"]), get_strings(accept_criteria),
        get_strings(note), story_json["id"])
    print(s)

def make_story_name(prefix, number):
    if prefix is None or prefix == "":
        return str(number)
    else:
        return prefix + "-" + str(number)

def find_story(organisation, project, number, prefix=None):
    story_name = make_story_name(prefix, number)
    stories = search_stories(organisation, project, story_name)
    # TODO: hvad hvis len(items) er < count
    for story in stories["items"]:
        if prefix is not None and prefix != story["prefix"]:
            continue
        if story["number"] == number:
            return story["id"]
    return -1

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

def set_auth(args, config):
    global auth
    if args.auth is None and config is not None and "auth" in config:
        auth = config["auth"]
    elif args.auth is not None:
        auth = args.auth
    else:
        user = input("scrumdo username: ")
        psswd = getpass.getpass("scrumdo password: ")
        auth = base64.b64encode("{}:{}".format(user, psswd).encode("utf8"))
        auth = auth.decode("utf8")

if __name__ == "__main__":
    args = setup_args()
    config = read_config(args.config_file)
    set_auth(args, config)

    parts = re.search("([a-zA-Z]+)?-?(\d+)", args.story_name)
    if parts is None:
        print("unknown story id format: {}".format(sys.argv[1]),
            file=sys.stderr)
        sys.exit(1)
    prefix = parts.groups()[0]
    number = parts.groups()[1]
    story_id = find_story(args.organization, args.project, int(number), prefix)
    if story_id != -1:
        print_story(get_story(args.organization, args.project, story_id))
