import sys
import json
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta

sys.path.insert(0, "..")
sys.path.insert(0, ".")

import caldav

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

with open("config/config.json", "r") as config_file:
    config = json.load(config_file)
with open("config/emoji_dict.json", "r") as emoji_file:
    emoji_dict = json.load(emoji_file)

caldav_url = config["caldav_url"]
username = config["username"]
password = config["password"]
headers = {"X-MY-CUSTOMER-HEADER": "123"}
calendar_to_sync = config["calendar_to_sync"]

def print_calendars(calendars):
    if calendars:
        logger.info("Your principal has %i calendars:", len(calendars))
        for c in calendars:
            logger.debug("    Name: %-36s  URL: %s", c.name, c.url)
    else:
        logger.debug("Your principal has no calendars")

def update_emoji_dict(word,emoji):
    """
    Update the emoji_dict with a new word and emoji.
    If the word already exists in the emoji_dict, no changes are made.
    """
    emoji_dict[word] = emoji
    with open("config/emoji_dict.json", "w", encoding="utf-8") as emoji_file:
        json.dump(emoji_dict, emoji_file, indent=4, ensure_ascii=False)
    return True
def add_words_to_emoji_dict(words, emoji="❓"):
    """
    Add a word or list of words to the emoji_dict with the given emoji.
    If the word already exists in the emoji_dict, no changes are made.
    """
    first_word=words[0]
    found = False
    for word in words:
        if word == "":
            logger.debug("Skipping empty word")
            pass
        elif first_word=="":
                logger.debug("first word is empty, setting it to '%s'", word)
                first_word=word #the first word is the one we want to add
        elif word in emoji_dict:
            
            if (emoji_dict[word] != emoji):
                if (emoji == "❓"):
                    logger.debug("Trying to update '%s' emoji to default. Current emoji is '%s'. doing nothing", word, emoji_dict[word])
                if (emoji_dict[word] == "❓"):
                    # If the emoji is not set, update it
                    logger.debug("'%s' already exists in emoji_dict with default. Updating to '%s'.", word, emoji)
                    update_emoji_dict(word, emoji)
                else:
                    logger.debug("'%s' already exists in emoji_dict with emoji '%s', updating to '%s'.", word, emoji_dict[word], emoji)
                update_emoji_dict(word, emoji)
            else:
                logger.debug("'%s' already exists in emoji_dict with the same emoji '%s'.", word, emoji)
                # No changes needed, just log it
            found=True
            break #if one word is found, we can stop checking the rest of the words
            

    if not found:
        logger.debug("Adding '%s' to emoji_dict with emoji '%s'.", first_word, emoji)
        update_emoji_dict(first_word, emoji)

    return found

def words_to_emoji(words):
    """
    Convert a word to an emoji using the emoji_dict.
    If the word is not in the emoji_dict, add it with a default emoji.
    """
    found = False
    for word in words:
        # check each word
        if word in emoji_dict:
            logger.debug("Found '%s' in emoji_dict with emoji '%s'.", word, emoji_dict[word])
            return emoji_dict[word]
            

    # if no word is found, add the first word to the emoji_dict with a default emoji
    if not found:
        logger.debug("Adding '%s' to emoji_dict with default emoji.", words)
        add_words_to_emoji_dict(words)

    return "❓"


if __name__ == "__main__":
    with caldav.DAVClient(
        url=caldav_url,
        username=username,
        password=password,
        headers=headers,
    ) as client:
        my_principal = client.principal()
        calendars = my_principal.calendars()
        # print_calendars(calendars)

        dev_calendar = my_principal.calendar(name=calendar_to_sync)
        logger.info("Working with calendar: %s", dev_calendar.name)
        events = dev_calendar.search(
            start=datetime.now(),
            end=datetime(date.today().year + 1, 1, 1),
            event=True,
            expand=False,
        )
        logger.info("Found %i events", len(events))
        for event in events:
            event_name = event.icalendar_component.get("summary")
            logger.debug("##Event: %s", event_name)
            if event_name[0].isalpha(): #the event name starts with a letter
                logger.debug("This event does not start with an emoji, let's add that")

                assert len(event.wire_data) >= len(event.data)
                summary_parts = event_name.split(" ")
                logger.debug("Words: %s", summary_parts)
                emoji = words_to_emoji(summary_parts)

                event.vobject_instance.vevent.summary.value = emoji + " " + event_name

                event.save()
            elif (event_name[0] == "❓"):
                # The event name starts with the default emoji, we can still try and add a emoji to this word
                
                event_name = event_name[1:]  # Remove the first character (default emoji) from the event name
                summary_parts = event_name.split(" ")
                emoji = words_to_emoji(summary_parts)
                logger.debug("This event starts with the default emoji, the emoji available is: %s", emoji)
                if not emoji:
                    # no emoji found, do nothing (already has the default emoji)
                    pass
                elif emoji == "❓":
                    # no emoji found, do nothing (already has the default emoji)
                    pass
                elif emoji:
                    event.vobject_instance.vevent.summary.value = emoji + " " + event_name
                    event.save()
            else:
                logger.debug("This event already starts with an emoji, check if the word and emoji is known and/or add it to the emoji_dict")
                if(event_name[1] == " "):
                    # If the event name starts with an emoji followed by a space, split the string on spaces
                    # into emoji and word
                    
                    summary_parts = event_name.split(" ")
                    
                    emoji = summary_parts.pop(0) # pop the first character which is the emoticon
                    words = summary_parts #the rest of the string are the words
                    logger.debug("splitting with spaces. Emoji: %s Words: %s", emoji, words)
                else:
                    # If the event name starts with an emoji followed by a word, split the string
                    # into emoji and word
                    # This is a workaround for the case where the emoji is not followed by a space
                    # but by a letter or number
                    # For example: "🚀Launch" instead of "🚀 Launch"
                    summary_parts = event_name.split(" ")
                    emoji = summary_parts[0][0]  # Get the first character (emoji) from the first item
                    summary_parts[0] = summary_parts[0][1:]  # Remove the first character (emoji) from the string
                    words = summary_parts 
                    logger.debug("splitting no space. Emoji: %s Words: %s", emoji, words)
                add_words_to_emoji_dict(words, emoji)
            logger.debug("")

        logger.debug("End of script")