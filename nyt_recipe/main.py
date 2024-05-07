#!/usr/bin/env python3
# (c) 2021 Ian Brault
# This code is licensed under the MIT License (see LICENSE.txt for details)

import argparse
import os
import sys

import requests

from .output import *
from .recipe import Recipe


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Downloads recipes from NYT Cooking and saves them in a "
        "styled HTML and Markdown format")

    parser.add_argument("url", metavar="URL", nargs="*")
    parser.add_argument(
        "-o", "--output", metavar="PATH",
        default=os.path.join(os.environ["HOME"], "recipes"),
        help="Output directory, defaults to ~/recipes"
    )
    parser.add_argument("-f", "--file", metavar="PATH",
                        help="A file holding a list of urls to download. URL(s) will be appended")
    
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debug output")
    parser.add_argument("-t", "--no-html", action="store_true",
                        help="Disable HTML output")
    parser.add_argument("-m", "--no-md", action="store_true",
                        help="Disable Markdown output")
    parser.add_argument("-e", "--no-embed", action="store_true",
                        help="Disables embedding images as data-uris, saves to file")
    parser.add_argument("-s", "--save-imgs",
                        action="store_true", help="Save images to file, even if embedding"
                        )
    
    return parser.parse_args(args)


def save_recipe(recipe, args):
    # create the output path if it does not already exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # dump the recipe to a file
    stem = recipe.title.lower().replace(" ", "_").replace("'", "")
    recipe_file = os.path.join(args.output, f"{stem}.html")
    recipe_file_md = os.path.join(args.output, f"{stem}.md")
    debug(f"saving to {recipe_file}")
    if not args.no_html:
        try:
            with open(recipe_file, "w") as f:
                f.write(recipe.to_html())
        except (IOError, OSError) as ex:
            error(f"failed to write the recipe file {recipe_file}")
            debug(str(ex))

    if not args.no_md:
        try:
            with open(recipe_file_md, "w") as f:
                f.write(recipe.to_md())
        except (IOError, OSError) as ex:
            error(f"failed to write the recipe file {recipe_file_md}")
            debug(str(ex))

    if args.no_html:
        print(f"Saved recipe \"{recipe.title}\" to {recipe_file_md}")
    elif args.no_md:
        print(f"Saved recipe \"{recipe.title}\" to {recipe_file}")
    else:
        print(f"Saved recipe \"{recipe.title}\" to {recipe_file} and {recipe_file_md}")


def download_and_save_recipe(url, args):
    # get the raw recipe HTML
    try:
        debug(f"fetching from {url}")
        raw = requests.get(url).text
    except requests.exceptions.RequestException as ex:
        error(f"failed to get the recipe from {url}")
        debug(str(ex))

    # extract the recipe from the HTML and save off to a file
    recipe = Recipe.from_html(raw, args, url)
    save_recipe(recipe, args)


def main():
    try:
        args = parse_args(sys.argv[1:])
        toggle_debug(args.debug)
        if args.url == None:
            args.url = []
        if not args.file == None:
            file = open(args.file, "r")
            urls = file.readlines()
            args.url += urls
        if not isinstance(args.url, list):
            args.url += [args.url]
        for url in args.url:
            download_and_save_recipe(url, args)
    except KeyboardInterrupt:
        pass
