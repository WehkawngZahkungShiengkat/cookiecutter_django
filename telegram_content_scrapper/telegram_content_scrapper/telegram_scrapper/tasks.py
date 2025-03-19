import os
import sys
from typing import Optional
from celery import shared_task
from datetime import datetime
import time, asyncio
from asgiref.sync import sync_to_async, async_to_sync
from .telethon_funcs import get_entity_object, session_validation, telethon_user_entities, fetch_entity_contents
from .models import TelegramEntity, TelegramEntityContentData, TelegramUserEntity
from django.db.models import Min, Count
from billiard.exceptions import SoftTimeLimitExceeded

def delete_duplicate_contents():
    print(">>>>>> DEBUG - Delete duplicated rows")
    duplicates = (
        TelegramEntityContentData.objects
        .values("telegram_entity_id", "content_id")
        .annotate(oldest_id=Min("id"))  # Get the oldest record's ID
    )

    # Get IDs of records to keep
    keep_ids = {entry["oldest_id"] for entry in duplicates}

    # Delete all records that are not in keep_ids
    deleted_count, _ = TelegramEntityContentData.objects.exclude(id__in=keep_ids).delete()
    
    print(f"Deleted {deleted_count} duplicate rows.")


DEFAULT_TELEGRAM_MSG_PER_FETCH = 100
@shared_task(bind=True)
def load_user_telegram_entities(self, user_id:int, session_data:bytes):
    try:
        data_return = async_to_sync(telethon_user_entities)(session_data)
        user_t_entities_data = data_return.get("entities",[])
        if not data_return.get("proc_successed", False):
            raise Exception(data_return.get("msg"))
        user_entity_records = TelegramUserEntity.objects.filter(user_id=user_id, is_still_linked=True)
        unlinked_user_entity_records = []
        current_user_entities_ids = list(i.get("entity_id") for i in user_t_entities_data)

        # filter latest user linked entities and unlinked entites
        for _record in user_entity_records:
            _record_entity_id = _record.telegram_entity.entity_id
            if _record_entity_id in current_user_entities_ids:
                current_user_entities_ids.remove(_record_entity_id)
            else:
                unlinked_user_entity_records.append(_record)
        
        # update user unlinked entites
        for _record in unlinked_user_entity_records:
            _record.is_still_linked = False
            _record.save()

        # record new user linked entites
        for _each_data in user_t_entities_data:
            _entity_id = _each_data.get("entity_id")
            if _entity_id in current_user_entities_ids:
                entity_record = TelegramEntity.objects.filter(entity_id=_entity_id).first()
                if entity_record is not None:
                    user_entity_record = TelegramUserEntity.objects.filter(telegram_entity_id=entity_record.id, user_id=user_id).first()
                    if user_entity_record is not None:
                        if not user_entity_record.is_still_linked:
                            user_entity_record.is_still_linked = True
                            user_entity_record.save()
                    else:
                        new_user_entity_record = TelegramUserEntity(user_id=user_id, telegram_entity_id=entity_record.id)
                        new_user_entity_record.save()
                else:
                    _entity_type = _each_data.get("entity_type")
                    _entity_name = _each_data.get("entity_name")
                    new_entity_record = TelegramEntity(entity_id=_entity_id, entity_type=_entity_type, entity_name=_entity_name)
                    new_entity_record.save()

                    new_user_entity_record = TelegramUserEntity(user_id=user_id, telegram_entity_id=new_entity_record.id)
                    new_user_entity_record.save()
    except Exception as e:
        error = f"Error - {e}"
        print(f"xxxxxxxxxx {error}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        self.update_state(state='FAILURE', meta={'exc': e})


@shared_task(bind=True, soft_time_limit=180)
def load_user_telegram_entity_contents(self, user_id:int, session_data:bytes, telegram_entity_id_pk:int, min_content_id:Optional[int]=None):
    try:
        fetch_limit = DEFAULT_TELEGRAM_MSG_PER_FETCH
        _max_proc_time = 174
        self.update_state(state='STARTED', meta={'message': 'Task started'})
        validation_result = async_to_sync(session_validation)(session_data)
        _is_valid_session = validation_result.get("is_valid")
        _task_proc_start_at = time.monotonic()
        
        telegram_entity_data = TelegramEntity.objects.filter(id=telegram_entity_id_pk).first()
        if telegram_entity_data is not None and _is_valid_session:
            telegram_entity_id = telegram_entity_data.entity_id
            validated_user_entity_data = async_to_sync(get_entity_object)(session_data, telegram_entity_id)
            telegram_entity_object = validated_user_entity_data.get("entity_found")
            if telegram_entity_object is not None:
                fetch_contents_return_list_len = fetch_limit
                print(f"Min Content id - {min_content_id}({type(min_content_id)})")
                if min_content_id is not None and min_content_id > 0:
                    latest_telegram_entity_content_contentID = min_content_id
                else:
                    latest_telegram_entity_content_data = TelegramEntityContentData.objects.filter(
                        telegram_entity_id=telegram_entity_id_pk
                    ).order_by("-content_id").first()
                    latest_telegram_entity_content_contentID = (
                        latest_telegram_entity_content_data.content_id
                        if latest_telegram_entity_content_data
                        else 0
                    )
                print(f">>>>> DEBUG <<<< latest_telegram_entity_content_contentID - {latest_telegram_entity_content_contentID}")
                # fetch 100 contents at a time until no data to left to fetch
                while (fetch_contents_return_list_len == fetch_limit) and (time.monotonic() < _task_proc_start_at + _max_proc_time):
                    # print(f">>>>>> DEGUB Current fetching for latest_telegram_entity_content_contentID - {latest_telegram_entity_content_contentID}")
                    data_return = async_to_sync(fetch_entity_contents)(session_data, telegram_entity_object, latest_telegram_entity_content_contentID, fetch_limit)
                    user_t_entities_data = data_return.get("retrieved_contents",[])
                    fetch_contents_return_list_len = len(user_t_entities_data)
                    # print(f">>>>>> DEGUB <<<<<< ---- fetch_contents_return_list_len - {fetch_contents_return_list_len}")
                    if not data_return.get("proc_successed", False):
                        raise Exception(data_return.get("msg"))
                    for _each_data in user_t_entities_data:
                        _telegram_entity_content_data = TelegramEntityContentData.objects.filter(telegram_entity_id=telegram_entity_id_pk,content_id=_each_data["content_id"]).first()
                        if _telegram_entity_content_data is None:
                            # print(f">>>>>> DEGUB <<<<<< ---- Each user_t_entities_data - {_each_data}")
                            _new_telegram_entity_content_data = TelegramEntityContentData(content_id=_each_data["content_id"], entity_text_content=_each_data["entity_text_content"], entity_media_data_content=_each_data["entity_media_data_content"], entity_media_data_type=_each_data["entity_media_data_type"], entity_content_url=_each_data["entity_content_url"], entity_post_timestamp=_each_data["entity_post_timestamp"], processed_text_content=_each_data["processed_text_content"], text_content_hashtags=_each_data["text_content_hashtags"], date_in_text_content=_each_data["date_in_text_content"], time_in_text_content=_each_data["time_in_text_content"],updated_by_id=user_id, telegram_entity_id=telegram_entity_id_pk)

                            _new_telegram_entity_content_data.save()
                            latest_telegram_entity_content_contentID = _new_telegram_entity_content_data.content_id
                            # print(f">>>>>> DEGUB <<<<<< ---- latest_telegram_entity_content_contentID - {latest_telegram_entity_content_contentID}")
                        else:
                            _telegram_entity_content_data.entity_content_url = _each_data["entity_content_url"]
                            _telegram_entity_content_data.processed_text_content = _each_data["processed_text_content"]
                            _telegram_entity_content_data.text_content_hashtags = _each_data["text_content_hashtags"]
                            _telegram_entity_content_data.date_in_text_content = _each_data["date_in_text_content"]
                            _telegram_entity_content_data.time_in_text_content = _each_data["time_in_text_content"]
                            _telegram_entity_content_data.save()
                            latest_telegram_entity_content_contentID = _telegram_entity_content_data.content_id
                            print(f">>>>>> DEGUB <<<<<< ---- latest_telegram_entity_content_contentID - {latest_telegram_entity_content_contentID}")
                    time.sleep(1)
                self.update_state(state='SUCCESS', meta={'message': 'Task started'})
            else:
                if not validated_user_entity_data.get("proc_successed"):
                    raise Exception(validated_user_entity_data.get("msg"))
    except SoftTimeLimitExceeded:
        self.update_state(state='FAILURE', meta={'exc': 'SoftTimeLimitExceeded'})
        return
    except Exception as e:
        error = f"Error - {e}"
        print(f"xxxxxxxxxx {error}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        self.update_state(state='FAILURE', meta={'exc': e})

