#!/usr/bin/python3

import optparse
import re
import subprocess
import sys

class Args(object):
    """container for commandline arguments"""
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return self.__dict__ != other.__dict__
    def __repr__(self):
        return "Args(%s)" % str(self.__dict__)

class Record(dict):
    def __init__(self, record_string):
        for line in record_string.split("\n"):
            field_name = line[:line.find(" ")]
            if field_name not in self:
                self[field_name] = []
            self[field_name].append(line)

    def __str__(self):
        fields = [self[k] for k in sorted(self.keys())]
        fields_flattened = [a for b in fields for a in b]
        return "\n".join(fields_flattened) + "\n"

def setup_args():
    usage = """%prog files [OPTIONS]

positional arguments:
    files\t\tone or more files to search through. can be either plain or gzipped.

example:
    %prog -s 245 "mise? en sc[eèé]ne" /data/danbib/870970/2016* -f 001,245"""
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-g", "--general-search", metavar="pattern",
        help="pattern to search for in all fields. ex: \"009 00.*?\*am\"")
    parser.add_option("-s", "--search", metavar="field pattern",
        action="append", nargs=2,
        help="search individual fields. ex: -s 009 \"\*am\". can be "
        "specified any number of times")
    parser.add_option("-f", "--fields", metavar="fields",
        help="fields to output, separated by commas")
    (options, positional_args) = parser.parse_args()

    if len(positional_args) < 1:
        parser.error("too few arguments")
    if options.search is None and options.general_search is None:
        parser.error("missing -s or -g")
    if options.search is not None and options.general_search is not None:
        parser.error("-s and -g are mutualy exclusive")

    # optparse understøtter ikke navngivne positionsargumenter,
    # så det her er en efterligning af udseendet i argparse
    args = Args()
    args.files = positional_args
    for key, value in options.__dict__.items():
        setattr(args, key, value)

    return args

def main():
    args = setup_args()
    for f in args.files:
        if f[-3:] == ".gz":
            uncompress = subprocess.Popen(["zcat", f], stdout=subprocess.PIPE)
            t = subprocess.check_output(["semarc"], stdin=uncompress.stdout)
        else:
            t = subprocess.check_output(["semarc", f])
        t = t.decode("latin-1")
        records = t.split("\n\n")
        for r in records:
            r = Record(r)
            found = False
            if args.search is not None:
                f_dict = {field: False for field, _ in args.search}
                for field, query in args.search:
                    if field in r:
                        for f in r[field]:
                            if re.search(query, f) is not None:
                                f_dict[field] = True
                                break
                found = False not in f_dict.values()
            elif args.general_search is not None:
                for field in r.values():
                    if re.search(args.general_search, "\n".join(field)) is not None:
                        found = True
                        break
            if found:
                if args.fields is not None and args.fields != "":
                    for fld in args.fields.split(","):
                        if fld in r:
                            print("\n".join(r[fld]))
                else:
                    print(r)
                print()

if __name__ == "__main__":
    main()
