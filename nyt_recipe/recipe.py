# (c) 2021 Ian Brault
# This code is licensed under the MIT License (see LICENSE.txt for details)

import os
import bs4

import re

import requests

import data_url

from .output import *


TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/light.css">
    <meta charset="UTF-8">
</head>
<body>
    <main class="wrapper">
        <section class="container" id="header">
            <img style="display:block;margin-left:auto;margin-right:auto;" src="{image}" alt="{title}"/>
            <h1 style="text-align:center;">{title}</h1>
            <p style="text-align:center;">
                <em><a href="{og_link}" target="_blank">{og_link}</a></em>
                <br>
                <em>{serving_size}</em>
                 - 
                <em>{total_time}</em>
            </p>
        </section>
        <section id="ingredients">
            <h2>Ingredients</h2>
            <ul>
                {ingredients}
            </ul>
        </section>
        <section id="instructions">
            <h2>Instructions</h2>
            <ol>
                {instructions}
            </ol>
        </section>
    </main>
</body>
</html>
"""

TEMPLATE_MD = """\
# {title}

![{title}]({image})

[{og_link}]({og_link})

*{serving_size}* - *{total_time}*

## Ingredients

{ingredients}

## Instructions

{instructions}
"""


def _image_from_soup(soup, args, stem):
    image = ""
    image_file_name = f"{stem}.header.webp"
    image_file = os.path.join(args.output, image_file_name)
    class_re = re.compile(r"recipeheaderimage_image__.+")

    header_image = soup.find(
        "div", attrs={"class": class_re}).select("img")[0]["src"]
    if not header_image:
        warn("recipe is missing header image")
        return image

    image_data = bytes()
    local_read = False
    if os.path.isfile(image_file):
        debug(f"Reading local image file {image_file}")
        try:
            with open(image_file, "rb") as f:
                image_data = f.read()
                local_read = True
        except (IOError, OSError) as ex:
            error(f"failed to read the image file {image_file}")
            debug(str(ex))
    else:
        debug(f"Downloading image file {header_image}")
        image_data = requests.get(header_image).content

    image = data_url.construct_data_url(
        mime_type='image/webp', base64_encode=True, data=image_data)
    if (args.no_embed or args.save_imgs) and not local_read:
        try:
            with open(image_file, "wb") as f:
                f.write(image_data)
        except (IOError, OSError) as ex:
            error(f"failed to write the image file {image_file}")
            debug(str(ex))
    else:
        debug("Not writing image to file")

    return (image, image_file_name)


def _title_from_soup(soup):
    title = soup.title.string
    if title is None:
        warn("recipe is missing a title")
        title = ""
    # strip the " - NYT Cooking" suffix and "Recipe"
    title = title.replace(" Recipe", "").replace(" - NYT Cooking", "").strip()

    debug(f"title: {title}")
    return title


def _serving_size_from_soup(soup):
    serving = ""

    yield_span = soup.find("span", string="Yield:")
    if yield_span is None:
        warn("recipe is missing a serving size")
        return serving
    serving_span = yield_span.next_sibling
    if serving_span is None:
        warn("recipe is missing a serving size")
        return serving

    serving = serving_span.text.strip()
    debug(f"serving size: {serving}")
    return serving


def _total_time_from_soup(soup):
    total_time = ""

    tt_span = soup.find("dt", string="Total Time")
    if tt_span is None:
        warn("recipe is missing a total_time")
        return total_time
    total_time_span = tt_span.next_sibling
    if total_time_span is None:
        warn("recipe is missing a total_time")
        return total_time

    total_time = total_time_span.text.strip()
    debug(f"total time: {total_time}")
    return total_time


def _ingredients_from_soup(soup):
    ingredients = []
    class_re = re.compile(r"ingredient_ingredient__.+")

    ingredients_list = soup.findAll("li", attrs={"class": class_re})
    if not ingredients_list:
        warn("recipe is missing ingredients")
        return ingredients

    for item in ingredients_list:
        ingredient = " ".join(tag.text.strip() for tag in item.children)
        debug(f"ingredient: {ingredient}")
        ingredients.append(ingredient)

    return ingredients


def _instructions_from_soup(soup):
    instructions = []
    class_re = re.compile(r"preparation_step__.+")

    instructions_list = soup.findAll("li", attrs={"class": class_re})
    if not instructions_list:
        warn("recipe is missing instructions")
        return instructions

    for item in instructions_list:
        step_tag = item.find("p", attrs={"class": "pantry--body-long"})
        if not step_tag:
            warn("instruction is missing text")
            continue
        instruction = step_tag.text.strip()
        debug(f"instruction: {instruction}")
        instructions.append(instruction)

    return instructions


class Recipe(object):
    def __init__(
        self,
        title="",
        serving_size="",
        total_time="",
        ingredients=[],
        instructions=[],
        image="",
        image_file="",
        stem="",
        no_embed=False,
        og_link="",
    ):
        self.title = title
        self.serving_size = serving_size
        self.total_time = total_time
        self.ingredients = ingredients
        self.instructions = instructions
        self.image = image
        self.image_file = image_file
        self.stem = stem
        self.no_embed = no_embed
        self.og_link = og_link

    def to_html(self):
        double_tab = " " * 16
        ingredients = "\n".join(
            f"{double_tab}<li>{i}</li>" for i in self.ingredients)
        instructions = "\n".join(
            f"{double_tab}<li>{i}</li>" for i in self.instructions)
        title = self.title.replace(" (", " <br>(")

        image = self.image
        if self.no_embed:
            image = self.image_file

        return TEMPLATE.format(
            title=title, serving_size=self.serving_size, total_time=self.total_time,
            ingredients=ingredients, instructions=instructions, image=image, og_link=self.og_link)

    def to_md(self):
        ingredients = "\n".join(
            f"* {i}" for i in self.ingredients)
        instructions = "\n".join(
            f"* {i}" for i in self.instructions)

        image = self.image
        if self.no_embed:
            image = self.image_file

        return TEMPLATE_MD.format(
            title=self.title, serving_size=self.serving_size, total_time=self.total_time,
            ingredients=ingredients, instructions=instructions, image=image, og_link=self.og_link)

    @staticmethod
    def from_html(raw, args, og_link):
        soup = bs4.BeautifulSoup(raw, "html.parser")

        title = _title_from_soup(soup)
        serving_size = _serving_size_from_soup(soup)
        total_time = _total_time_from_soup(soup)
        ingredients = _ingredients_from_soup(soup)
        instructions = _instructions_from_soup(soup)
        stem = title.lower().replace(" ", "_").replace("'", "")
        image, image_file = _image_from_soup(soup, args, stem)

        return Recipe(
            title, serving_size, total_time, ingredients, instructions,
            image, image_file, stem, no_embed=args.no_embed, og_link=og_link
        )
