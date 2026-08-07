from flask import render_template
from jinja2 import Template
import typing as t

nav = [
    {"href":"/#top", "icon":"icons/home.html", "name":"Home", "active": False},
    {"href":"browse", "icon":"icons/search.html", "name":"Explore", "active": False},
    {"href":"", "icon":"icons/bell.html", "name":"Notifications", "active": False},
    {"href":"", "icon":"icons/chat.html", "name":"Chat", "active": False},
    {"href":"", "icon":"icons/grok.html", "name":"Grok", "active": False},
    {"href":"", "icon":"icons/bookmark.html", "name":"Bookmarks", "active": False},
    {"href":"", "icon":"icons/studio.html", "name":"Creator Studio", "active": False},
    {"href":"", "icon":"icons/premium.html", "name":"Premium", "active": False},
    {"href":"", "icon":"icons/profile.html", "name":"Profile", "active": False},
    {"href":"", "icon":"icons/more.html", "name":"More", "active": False},
]

def set_active(name):
    for element in nav:
        if element["name"] == name:
            element["active"] = True
        else:
            element["active"] = False
            
def render(
    template_name_or_list: str | Template | list[str | Template],
    **context: t.Any,
) -> str:
    context["navigation"] = nav
    return render_template(template_name_or_list, **context)