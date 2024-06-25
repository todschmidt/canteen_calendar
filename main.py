import wpparser
from pprint import pp

DEBUG=False

events = wpparser.parse("./export-events.xml")

if DEBUG: pp(events)

for event in events["posts"]:
    if "tribe_events" in post.get("post_type"):
        pp(event)