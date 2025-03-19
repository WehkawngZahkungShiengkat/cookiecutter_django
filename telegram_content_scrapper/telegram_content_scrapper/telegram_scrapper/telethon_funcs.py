import base64
import sys
import unicodedata
from django.test import TestCase

# Create your tests here.

import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel, MessageMediaDocument, MessageMediaPhoto

# from telegram_content_scrapper.telegram_scrapper.telethon_db_session import DjangoTelethonSession
from cryptography.fernet import Fernet
import environ
import re
import datetime

env = environ.Env()

TBOT_TOKEN = env("TBOT_TOKEN", default="")
API_ID = env("API_ID", default="")
API_HASH = env("API_HASH", default="")

# 1. get the key
def custom_generate_key(api_id:str, api_hash:str):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=api_id.encode(),
        iterations=1_000_000,
    )

    key = base64.urlsafe_b64encode(kdf.derive(api_hash.encode()))

    return key

# 2. Encrypt the session string
def encrypt_session_data(session_str:str, api_id:str, api_hash:str) -> bytes:
    """
    Encrypts the session string using the provided key.
    """
    f = Fernet(custom_generate_key(api_id, api_hash))
    encrypted_string = f.encrypt(session_str.encode())  # Encode to bytes
    return encrypted_string

# 3. Decrypt the session string
def decrypt_session_data(encrypted_data:bytes, api_id:str, api_hash:str):
    """
    Decrypts the encrypted session string using the provided key.
    """
    f = Fernet(custom_generate_key(api_id, api_hash))
    decrypted_string = f.decrypt(encrypted_data).decode()  # Decode from bytes
    return decrypted_string


def to_single_line_text(text:str, content_post_date: datetime.date):
    # 1) Convert new lines (\n) to white space
    text = text.replace("\n", " ")

    # 2) Remove icons, emojis, and symbols
    text = "".join(char for char in text if unicodedata.category(char)[0] not in ["S", "C"])

    # 3) Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text).strip()

    time_found, date_found, hash_tage, text = extract_data_from_text(text, content_post_date)
    print(f"{type(time_found)} - {time_found}")
    print(f"{type(date_found)} - {date_found}")
    print(f"{type(hash_tage)} - {hash_tage}")
    return time_found, date_found, hash_tage, text

def extract_data_from_text(text: str, reference_date: datetime.date):
    """
    Extract time objects, date objects, and hashtags from text, and return cleaned text.
    
    Time formats supported:
    - HH:MM (12hr or 24hr)
    - HH:MM:SS (12hr or 24hr)
    - With or without AM/PM indicators
    
    Date formats supported:
    - Short month name and day (Jan 1)
    - Full month name and day (January 1)
    - Month number and day (1/1 or 01/01)
    - With or without year (if no year, the year from reference_date is used)
    
    Hashtags:
    - Extracts words starting with # symbol
    
    Parameters:
    - text: The input text to extract information from
    - reference_date: A date object used to determine the current year for dates without a year
                      If None, today's date is used
    
    Returns:
    - Tuple of (time_object, date_object, hashtag_list, cleaned_text)
    """
    time_obj = None
    date_obj = None
    hashtags = []
    cleaned_text = text
    
    # Use reference_date if provided, otherwise use today's date
    if reference_date is None:
        reference_date = datetime.date.today()
    
    # Get current year from reference_date
    current_year = reference_date.year
    
    # Extract time - MODIFIED to find all matches and use the last one
    time_pattern = r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*((?:AM|PM|am|pm)?)'
    time_matches = list(re.finditer(time_pattern, cleaned_text))
    
    if time_matches:
        for i in range(len(time_matches)):
            reversed_index = (i + 1) * (-1)
            try:
                # Get the last time match
                last_match = time_matches[reversed_index]
                
                hour = int(last_match.group(1))
                minute = int(last_match.group(2))
                second = int(last_match.group(3)) if last_match.group(3) else 0
                am_pm = last_match.group(4).upper() if last_match.group(4) else ''
                
                # Handle 12-hour clock
                if am_pm:
                    if am_pm == 'PM' and hour < 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                
                time_obj = datetime.time(hour, minute, second)
                
                # Remove the time from the text for cleaning
                full_time_match = last_match.group(0)
                cleaned_text = cleaned_text.replace(full_time_match, '')
                break
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
    # Define month mappings
    month_names = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }
    
    # Store all date matches to remove from text later
    date_matches_to_remove = []
    
    # Extract date using different patterns
    
    # Pattern 1: Month name and day with optional year
    # Examples: Jan 15, January 15, January 15 2023, January 15, 2023
    pattern1 = r'(?P<month>January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|July|Jul|August|Aug|September|Sep|Sept|October|Oct|November|Nov|December|Dec)[.\s]+(?P<day>\d{1,2})(?:[,\s]+(?P<year>\d{2,4}))?'
    date_match = re.search(pattern1, cleaned_text, re.IGNORECASE)
    
    if date_match:
        month_str = date_match.group('month').lower()
        month = month_names[month_str]
        day = int(date_match.group('day'))
        
        year = current_year
        if date_match.group('year'):
            year = int(date_match.group('year'))
            # Convert 2-digit year to 4-digit
            if year < 100:
                year += 2000 if year < 50 else 1900
        
        try:
            date_obj = datetime.date(year, month, day)
            date_matches_to_remove.append(date_match.group(0))
        except ValueError:
            # Invalid date, like February 30
            date_obj = None
    
    # Pattern 2: MM/DD/YYYY or MM/DD or MM-DD-YYYY or MM-DD
    # Examples: 01/15/2023, 1/15, 01-15-2023, 1-15
    if not date_obj:
        pattern2 = r'(?P<month>\d{1,2})[/.-](?P<day>\d{1,2})(?:[/.-](?P<year>\d{2,4}))?'
        date_match = re.search(pattern2, cleaned_text)
        
        if date_match:
            month = int(date_match.group('month'))
            day = int(date_match.group('day'))
            
            year = current_year
            if date_match.group('year'):
                year = int(date_match.group('year'))
                # Convert 2-digit year to 4-digit
                if year < 100:
                    year += 2000 if year < 50 else 1900
            
            try:
                date_obj = datetime.date(year, month, day)
                date_matches_to_remove.append(date_match.group(0))
            except ValueError:
                # Invalid date
                date_obj = None
    
    # Pattern 3: DD/MM/YYYY or DD/MM or DD-MM-YYYY or DD-MM (European format)
    # Only try this if pattern 2 failed or produced an invalid date
    # Examples: 15/01/2023, 15/01, 15-01-2023, 15-01
    if not date_obj and re.search(r'\d{1,2}[/.-]\d{1,2}', cleaned_text):
        pattern3 = r'(?P<day>\d{1,2})[/.-](?P<month>\d{1,2})(?:[/.-](?P<year>\d{2,4}))?'
        date_match = re.search(pattern3, cleaned_text)
        
        if date_match:
            day = int(date_match.group('day'))
            month = int(date_match.group('month'))
            
            # Only accept as DD/MM if day <= 31 and month <= 12
            if day <= 31 and month <= 12:
                year = current_year
                if date_match.group('year'):
                    year = int(date_match.group('year'))
                    # Convert 2-digit year to 4-digit
                    if year < 100:
                        year += 2000 if year < 50 else 1900
                
                try:
                    date_obj = datetime.date(year, month, day)
                    date_matches_to_remove.append(date_match.group(0))
                except ValueError:
                    # Invalid date
                    date_obj = None
    
    # Extract hashtags
    hashtag_pattern = r'#(\w+)'
    hashtag_matches = re.finditer(hashtag_pattern, cleaned_text)
    
    for match in hashtag_matches:
        hashtags.append(match.group(1))  # Group 1 is the word without the # symbol
        
    # Remove hashtags and everythin after from cleaned text
    match = re.search(hashtag_pattern, cleaned_text)

    if match:
        # Find the starting position of the match
        start_index = match.start()
        # Return the string up to that position
        cleaned_text = cleaned_text[:start_index]
    
    # Remove date matches from cleaned text
    for date_str in date_matches_to_remove:
        cleaned_text = cleaned_text.replace(date_str, '')
    
    print(f"DEBUG - Before is {list(cleaned_text)}")
    # Clean up extra whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    # cleaned_text = re.sub(r'\s+', '', text)
    # Removes commas only if they are surrounded by spaces.
    # cleaned_text = re.sub(r'\s,\s', ' ', cleaned_text)
    cleaned_text = re.sub(r'\s+,\s*|\s*,\s+', '', cleaned_text)

    print(f"DEBUG - Before is {cleaned_text}")
    print(f"DEBUG - Before is {list(cleaned_text)}")
    # Removes the duplicated matched first word or word group until space
    cleaned_text = remove_continuous_duplicates(cleaned_text)
    print(f"DEBUG - After is {cleaned_text}")
    
    hashtags_list_str = ",".join(hashtags)
    return time_obj, date_obj, hashtags_list_str, cleaned_text

def remove_continuous_duplicates(text):
    """Removes continuous duplicate words from a string, using space as a delimiter."""
    words = text.split(" ")  # Split the text into a list of words
    cleaned_words = []
    previous_word = None

    for word in words:
        if word != '️':
            if previous_word is not None and previous_word in word:
                cleaned_words.remove(previous_word)
            previous_word = word
            cleaned_words.append(word)

    to_return =  " ".join(cleaned_words)  # Join the cleaned words back into a string
    return to_return

async def session_validation(session_data: bytes):
    data_returning = {
        "is_valid": False,
        "msg": "",
    }
    try:
        session_str = decrypt_session_data(session_data, API_ID, API_HASH)
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.connect()
        is_valid = await client.is_user_authorized()
        await client.disconnect()
        data_returning["is_valid"] = True
        print(f"(func) session_validation : {data_returning}")
        return data_returning
    except Exception as e:
        _err = f"error - {e}"
        data_returning["msg"] = _err
        print(f"(func) session_validation : {_err}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return data_returning

# def check_session_validation(session_str):
#     client = TelegramClient(StringSession(), int(API_ID), API_HASH)
#     retn_value = False
#     retn_value = client.loop.run_until_complete(session_validation(session_str))
#     return retn_value

# def send_verification_code(phone_number):
#     client = TelegramClient(StringSession(), int(API_ID), API_HASH)
#     retn_value = False
#     retn_value = client.loop.run_until_complete(telethon_send_code_request(phone_number))
#     return retn_value

async def telethon_send_code_request(phone_number):
    data_returning = {
        "phone_code_hash": None,
        "proc_successed": False,
        "msg": "",
        "instance_session": None,
    }
    try:
        print(f"(func) telethon_send_code_request : phone_number - {phone_number}")
        client = TelegramClient(StringSession(), int(API_ID), API_HASH)
        await client.connect()
        return_obj = await client.send_code_request(phone=phone_number)
        data_returning["phone_code_hash"] = return_obj.phone_code_hash
        _instance_session_str = client.session.save()
        _encrypted_session = encrypt_session_data(_instance_session_str, API_ID, API_HASH)
        data_returning["instance_session"] = _encrypted_session
        data_returning["proc_successed"] = True
        await client.disconnect()
    except Exception as e:
        data_returning["msg"] = f"error - {e}"
        print(f"(func) telethon_send_code_request : {data_returning}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
    return data_returning

async def telethon_verification_code_sign_in(phone_number, confirmation_code, phone_code_hash, instance_session_data):
    data_returning = {
        "encrypted_session": None,
        "proc_successed": False,
        "msg": ""
    }
    session_str = decrypt_session_data(instance_session_data, API_ID, API_HASH)
    try:
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.connect()
        await client.sign_in(phone=phone_number, code=confirmation_code, phone_code_hash=phone_code_hash)
        _session_str = client.session.save()
        _encrypted_session = encrypt_session_data(_session_str, API_ID, API_HASH)
        data_returning["encrypted_session"] = _encrypted_session
        data_returning["proc_successed"] = True
        print(f"(func - telethon_verification_code_sign_in) : {data_returning}")
    except Exception as e:
        _err = f"ERROR - {e}"
        print(f"(func - telethon_verification_code_sign_in) : {_err}")
        data_returning["msg"] = _err
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
    return data_returning

async def telethon_user_entities(session_data: bytes):
    data_returning = {
        "entities": [],
        "proc_successed": False,
        "msg": ""
    }
    try:
        _entities_list = []
        session_str = decrypt_session_data(session_data, API_ID, API_HASH)
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            _user_entities = await client.get_dialogs()
            for _each_entity in _user_entities:
                _entities_list.append(
                    {
                        "entity_name": _each_entity.name,
                        "entity_id": _each_entity.id,
                        "entity_type": _each_entity.entity.__class__.__name__
                    }
                )
            data_returning["entities"] = _entities_list
            data_returning["proc_successed"] = True
            await client.disconnect()
            # print(f"(func) telethon_user_entities : {data_returning}")
            return data_returning
        else:
            data_returning["proc_successed"] = False
            data_returning["msg"] = "User is not Authorized"
        await client.disconnect()
        # print(f"(func) telethon_user_entities : {data_returning}")
        return data_returning
    except Exception as e:
        _err = f"error - {e}"
        data_returning["msg"] = _err
        print(f"(func) telethon_user_entities : {_err}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return data_returning

def get_session(phone_number, confirmation_code, phone_code_hash):
    client = TelegramClient(StringSession(), int(API_ID), API_HASH)
    retn_value = False
    retn_value = client.loop.run_until_complete(telethon_verification_code_sign_in(phone_number, confirmation_code, phone_code_hash))
    return retn_value

async def get_entity_object(session_data:bytes, telegram_entity_id:int):
    data_returning = {
        "entity_found": None,
        "proc_successed": False,
        "msg": ""
    }
    try:
        session_str = decrypt_session_data(session_data, API_ID, API_HASH)
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            _user_dialogs = await client.get_dialogs()
            for _each_dialog in _user_dialogs:
                if _each_dialog.id == telegram_entity_id:
                    entity_info = await client.get_entity(_each_dialog)
                    data_returning["entity_found"] = entity_info
                    break
            data_returning["proc_successed"] = True
        else:
            data_returning["msg"] = "User is not Authorized"
        await client.disconnect()
        return data_returning
    except Exception as e:
        _err = f"error - {e}"
        data_returning["msg"] = _err
        print(f"(func) fetch_entity_contents : {_err}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return data_returning

async def fetch_entity_contents(session_data:bytes, telegram_entity, min_id:int, fetch_limit:int=100):
    data_returning = {
        "retrieved_contents": [],
        "proc_successed": False,
        "msg": ""
    }
    try:
        _content_list = []
        session_str = decrypt_session_data(session_data, API_ID, API_HASH)
        client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
        await client.connect()
        entity_id = telegram_entity.id

        contents = await client.get_messages(entity=telegram_entity, min_id=min_id, limit=fetch_limit, reverse=True)
        for _each in contents:
            content_id = _each.id
            content_text = _each.message
            content_post_timestamp =_each.date

            # Create the post link
            content_url_link = ""
            extracted_time_str = ""
            extracted_date_str = ""
            extracted_hashtags_str = ""
            processed_text_contact = ""
            # print(f"***********Is telegram_entity Channel - {isinstance(telegram_entity, Channel)}")
            # print(f"***********telegram_entity Type - {type(telegram_entity)}")
            if isinstance(telegram_entity, Channel):                        
                # Format: https://t.me/c/1234567890/123
                # For public channels: https://t.me/channelname/123
                if hasattr(telegram_entity, 'username') and telegram_entity.username:
                    # Public channel
                    content_url_link = f"https://t.me/{telegram_entity.username}/{content_id}"
                else:
                    # Private channel
                    # Convert negative ID to positive for the URL format
                    channel_id_str = str(entity_id)
                    if entity_id < 0:
                        channel_id_str = str(1000000000000 + abs(entity_id))
                    content_url_link = f"https://t.me/c/{channel_id_str}/{content_id}"
                    # print(f">>>>> DEBUG <<<< content_url_link - {content_url_link}")

            if content_text is not None and content_text != "":
                # print(f">>>>> DEBUG <<<< content_text - {content_text}")
                extracted_time, extracted_date, extracted_hashtags_str, processed_text_contact = to_single_line_text(content_text, content_post_timestamp.date())
                extracted_time_str = f"{extracted_time}" if extracted_time is not None else f"{content_post_timestamp.time()}"
                extracted_date_str = f"{extracted_date}" if extracted_date is not None else f"{content_post_timestamp.date()}"
            else:
                content_text = ""

            # print(f">>>>> DEBUG <<<< content_is - {content_id}")
            # print(f">>>>> DEBUG <<<< PASS before Media")
            media_data_in_bytes = None
            media_data_type = ""
            if isinstance(_each.media, MessageMediaPhoto):
                media_data_in_bytes = await client.download_media(_each.media, bytes)
                media_data_type = "png"
                # print(f"image condition 1 - {media_data_in_bytes}")
                # return image_bytes
            elif isinstance(_each.media, MessageMediaDocument):
                if _each.media.document.mime_type.startswith('image/'):
                    media_data_in_bytes = await client.download_media(_each.media, bytes)
                    media_data_type = "png"
                    # print(f"image condition 2 - {media_data_in_bytes}")
                    # return image_bytes
                elif _each.media.document.mime_type.startswith('application/') and hasattr(_each.media.document.attributes[0], "file_name"):
                    # file_bytes = await _each.download_media(_each.media, bytes)
                    media_data_in_bytes = await client.download_media(_each, bytes)
                    # print(f"image condition 3 - {media_data_in_bytes}")
                    media_data_type = _each.media.document.attributes[0].file_name.split('.')[-1] if _each.media.document.attributes[0].file_name else None
                    # print(f"file extension - {media_data_type}")
                    # return image_bytes
                else:
                    pass
                    # print("Media is not an image.")
            # print(f">>>>> DEBUG <<<< PASS After Media")  
            _content_list.append(
                {
                    "content_id": content_id,
                    "entity_text_content": content_text,
                    "entity_media_data_content": media_data_in_bytes,
                    "entity_media_data_type": media_data_type,
                    "entity_post_timestamp": content_post_timestamp,
                    "entity_content_url": content_url_link,
                    "processed_text_content": processed_text_contact, "text_content_hashtags": extracted_hashtags_str,
                    "date_in_text_content": extracted_date_str,
                    "time_in_text_content": extracted_time_str
                }
            )

        data_returning["retrieved_contents"] = _content_list
        data_returning["proc_successed"] = True
        # print(f"(func) fetch_entity_contents : if ending. Fetch data - {len(_content_list)}")
        await client.disconnect()
        # print(f"(func) fetch_entity_contents : {data_returning}")
        return data_returning
    except Exception as e:
        _err = f"error - {e}"
        data_returning["msg"] = _err
        print(f"(func) fetch_entity_contents : {_err}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return data_returning

