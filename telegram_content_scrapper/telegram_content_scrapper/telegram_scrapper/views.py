from datetime import timedelta, datetime
import json
import os
import sys
from django.shortcuts import render, redirect
from django.utils import timezone

# Create your views here.

from django.views import View
from django.views.generic.base import TemplateView
# from telegram_content_scrapper.telegram_scrapper.models import TelegramEntityInfo
from django.http import JsonResponse
from django.conf import settings
from .dummy_test_data import DATA
from telegram_content_scrapper.telegram_scrapper.forms import TelegramAuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from .telethon_funcs import telethon_send_code_request, session_validation, telethon_user_entities, telethon_verification_code_sign_in
from asgiref.sync import sync_to_async, async_to_sync
from .models import TelethonSession, TelegramUserEntity, TelegramEntityContentData
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from .tasks import load_user_telegram_entities, load_user_telegram_entity_contents
from celery.result import AsyncResult


DEFAULT_PER_FETCH = 1000

class UserTelegramEntitiesView(TemplateView):
    template_name = 'telegram_scrapper/telegram_entities_list.html'

    # Session Data in Browser Cookie storage
    def get(self, request, *args, **kwargs):
        try:
            user_id = request.user.id
            username = request.user.username
            phone_number_object = request.user.telegram_phone_number
            if phone_number_object is not None:
              telegram_phone_number = phone_number_object.as_e164
              load_user_telegram_session_data_str = request.COOKIES.get(f"{username}{telegram_phone_number}")
              if load_user_telegram_session_data_str is not None:
                  load_user_telegram_session_data = json.loads(load_user_telegram_session_data_str)
                  telegram_phone_hash = load_user_telegram_session_data.get("telegram_phone_hash")
                  telegram_session_str = load_user_telegram_session_data.get("telegram_session_str")
                  if telegram_session_str is not None:
                      data_returning = async_to_sync(session_validation)(telegram_session_str.encode())
                      _is_valid_session = data_returning.get("is_valid")
                      if _is_valid_session:
                          # update the user's latest telegram entities info in the background
                          load_user_telegram_entities.delay(user_id,telegram_session_str.encode())

                          # pull the current available user telegram entities info from database
                          user_entities_data = TelegramUserEntity.objects.filter(user_id=user_id, is_still_linked=True)
                          entities_types = []
                          entities_list = []
                          for user_entity in user_entities_data:
                              entity_info = user_entity.telegram_entity
                              entities_list.append(
                                  {
                                      "entity_id": entity_info.id,
                                      "entity_name": entity_info.entity_name,
                                      "entity_type": entity_info.entity_type,
                                  }
                              )
                          if len(entities_list):
                              entities_types = list(set(e.get("entity_type") for e in entities_list))
                          content = {
                              "entities_types": entities_types,
                              "options": entities_list
                          }
                          response = render(request, self.template_name, content)
                          response.set_cookie(
                              f"{username}{telegram_phone_number}",
                              load_user_telegram_session_data_str,
                              httponly=True,  # Prevent JavaScript access
                              # secure=True,  # Send only over HTTPS
                              samesite="Strict",  # Prevent CSRF attacks
                              max_age=432000  # set session age for 5 days
                          )
                          return response
            # any else got redirect to authentication
            return redirect('telegram:authentication')
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            _error = f"error - {e}"
            return render(request, "500.html", context={"exception": f"Error - {_error}"})


    # NOTE: session_data in database
    # def get(self, request, *args, **kwargs):
    #     try:
    #         user_id = request.user.id
    #         phone_number_object = request.user.telegram_phone_number
    #         _user_telegram_session = TelethonSession.objects.filter(owner_id=user_id, phone_number=phone_number_object).first()
    #         if _user_telegram_session is not None:
    #             _is_verified = _user_telegram_session.is_verified
    #             if _is_verified:
    #                 _session_data = _user_telegram_session.session_data
    #                 data_returning = async_to_sync(session_validation)(_session_data)
    #                 _is_valid_session = data_returning.get("is_valid")
    #                 if _is_valid_session:
    #                     # update the user's latest telegram entities info in the background
    #                     load_user_telegram_entities.delay(user_id,_session_data)

    #                     # pull the current available user telegram entities info from database
    #                     user_entities_data = TelegramUserEntity.objects.filter(user_id=user_id, is_still_linked=True)
    #                     entities_types = []
    #                     entities_list = []
    #                     for user_entity in user_entities_data:
    #                         entity_info = user_entity.telegram_entity
    #                         entities_list.append(
    #                             {
    #                                 "entity_id": entity_info.id,
    #                                 "entity_name": entity_info.entity_name,
    #                                 "entity_type": entity_info.entity_type,
    #                             }
    #                         )
    #                     if len(entities_list):
    #                         entities_types = list(set(e.get("entity_type") for e in entities_list))
    #                     content = {
    #                         "entities_types": entities_types,
    #                         "options": entities_list
    #                     }
    #                     response = render(request, self.template_name, content)
    #                     return response
    #                 _user_telegram_session.is_verified = False
    #                 _user_telegram_session.save()                    
    #         return redirect('telegram:authentication')
    #     except Exception as e:
    #         _error = f"error - {e}"
    #         return render(request, "500.html", context={"exception": f"Error - {_error}"})

    # def get(self, request, *args, **kwargs):
    #     try:
    #         user_id = request.user.id
    #         phone_number_object = request.user.telegram_phone_number
    #         _user_telegram_session = TelethonSession.objects.filter(owner_id=user_id, phone_number=phone_number_object).first()
    #         if _user_telegram_session is not None:
    #             _is_verified = _user_telegram_session.is_verified
    #             if _is_verified:
    #                 _session_data = _user_telegram_session.session_data
    #                 data_returning = async_to_sync(session_validation)(_session_data)
    #                 _is_valid_session = data_returning.get("is_valid")
    #                 if _is_valid_session:
    #                     user_entities_data = async_to_sync(telethon_user_entities)(_session_data)
    #                     print(f"(func) UserTelegramEntitiesView : {user_entities_data}")
    #                     entities_list = user_entities_data.get("entities",[])
    #                     context = {
    #                         # "entities": _recorded_user_entities
    #                         "entities_types": ["User", "Chat", "Channel"],
    #                         "options": entities_list
    #                     }
                        # response = render(request, self.template_name, context)
                        # celery_task_id = request.COOKIES.get("celery_task_id")
                        # # celery_task_id = None
                        # if celery_task_id:
                        #     if not AsyncResult(celery_task_id).ready(): # no new task will assign unless the status is SUCCESS or FAILURE
                        #         context = {
                        #             # "entities": _recorded_user_entities
                        #             "entities_types": ["User", "Chat", "Channel", f"Ready - {AsyncResult(celery_task_id).ready()}", f"Result - {AsyncResult(celery_task_id).result}", f"status - {AsyncResult(celery_task_id).status}"],
                        #             "options": entities_list
                        #         }
                        #         response = render(request, self.template_name, context)
                        #         return response
                        # celery_task_id = celery_testing.delay(_session_data)
                        # response.set_cookie(
                        #     "celery_task_id",
                        #     celery_task_id,
                        #     httponly=True,  # Prevent JavaScript access
                        #     # secure=True,  # Send only over HTTPS
                        #     samesite="Strict",  # Prevent CSRF attacks
                        #     max_age=86400  # 1 day expiry
                        # )
                        # return response
    #                 # else
    #                 _user_telegram_session.is_verified = False
    #                 _user_telegram_session.save()                    
    #         return redirect('telegram:authentication')
    #     except Exception as e:
    #         _error = f"error - {e}"
    #         return render(request, "500.html", context={"exception": f"Error - {_error}"})

user_telegram_entities_view = UserTelegramEntitiesView.as_view()

class TelegramUserAuthenticationView(LoginRequiredMixin, TemplateView):
    template_name = "telegram_scrapper/telegram_authentication.html"

    def get(self, request, *args, **kwargs):
        telegram_phone_number = None
        try:
            telegram_phone_number = request.user.telegram_phone_number.as_e164
            hidden_phone_number = (len(telegram_phone_number[0:len(telegram_phone_number)-4]) * '*') + telegram_phone_number[len(telegram_phone_number)-4:]
            form = TelegramAuthenticationForm()
            data = {
                "is_data_loaded": False,
                "messages": [],
                "loading_msg": f"Sending OTP code to  {hidden_phone_number}",
                "msg_need_attention": False,
                "form": form
            }
            return render(request, self.template_name, data)
        except Exception as e:
            _error = f"error - {_error}"
            if telegram_phone_number is None:
                data = {
                    "is_data_loaded": False,
                    "messages": [f"Connot find Telegram Account Phone Number.", "Please provide Telegram Account Phone Number."],
                    "msg_need_attention": True,
                    "form": form
                }

    def post(self, request, *args, **kwargs):
        try:
            form = TelegramAuthenticationForm(request.POST)
            data = {
                    "is_data_loaded": True,
                    "messages": [],
                    "loading_msg": None,
                    "msg_need_attention": False,
                    "form": form
                }
            if form.is_valid():
                user_id = request.user.id
                username = request.user.username
                phone_number_object = request.user.telegram_phone_number
                if phone_number_object is not None:
                    phone_number = phone_number_object.as_e164
                    otp_code = form.cleaned_data['code']
                    load_user_telegram_session_data_str = request.COOKIES.get(f"{username}{phone_number}")
                    if load_user_telegram_session_data_str is not None:
                        load_user_telegram_session_data = json.loads(load_user_telegram_session_data_str)
                        telegram_phone_hash = load_user_telegram_session_data.get("telegram_phone_hash")
                        telegram_session_str = load_user_telegram_session_data.get("telegram_session_str")
                        if telegram_phone_hash is not None and telegram_session_str is not None:
                            data_returning = async_to_sync(telethon_verification_code_sign_in)(phone_number, otp_code, telegram_phone_hash, telegram_session_str.encode())
                            session_data = data_returning.get("encrypted_session")
                            if session_data is not None:
                                telegram_session_data = {
                                    "telegram_phone_hash": telegram_phone_hash,
                                    "telegram_session_str": session_data.decode()
                                }
                                response = redirect('telegram:contents')
                                response.set_cookie(
                                    f"{username}{phone_number}",
                                    json.dumps(telegram_session_data),
                                    httponly=True,  # Prevent JavaScript access
                                    # secure=True,  # Send only over HTTPS
                                    samesite="Strict",  # Prevent CSRF attacks
                                    max_age=432000  # set session age for 5 days
                                )
                                return response
                            else:
                                data["messages"] = [
                                    f"Unsuccessful Verification. The OTP code {otp_code} is not correct.", "Re-enter the OTP code again or Resend Code to get new OTP code"
                                    ]
                                data["msg_need_attention"] = True
                                hidden_phone_number = (len(phone_number[0:len(phone_number)-4]) * '*') + phone_number[len(phone_number)-4:]
                                data["loading_msg"] = f"Resending OTP code to  {hidden_phone_number}"
                                return render(request, self.template_name, data)
                             
            data["messages"] = [
                f"Data missing for Telegram Authentication.", "Resend code to try again."
            ]
            data["msg_need_attention"] = True
            hidden_phone_number = (len(phone_number[0:len(phone_number)-4]) * '*') + phone_number[len(phone_number)-4:]
            data["loading_msg"] = f"Resending OTP code to  {hidden_phone_number}"
            return render(request, self.template_name, data)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            err_found = f"Error - {e}"
            return render(request, "500.html", context={"exception": err_found})

    # Prev Code with Database
    # def post(self, request, *args, **kwargs):
    #     form = TelegramAuthenticationForm(request.POST)
    #     err_found = "No Error Found"
    #     data = {
    #             "is_data_loaded": True,
    #             "messages": [],
    #             "loading_msg": None,
    #             "msg_need_attention": False,
    #             "form": form
    #         }
    #     if form.is_valid():
    #         user_id = request.user.id
    #         try:
    #             phone_number_object = request.user.telegram_phone_number
    #             phone_number = phone_number_object.as_e164
    #             otp_code = form.cleaned_data['code']
    #             user_tsession_data = TelethonSession.objects.filter(owner_id=user_id, phone_number=phone_number_object).first()
    #             if user_tsession_data is not None:
    #                 phone_number_hash= user_tsession_data.phone_number_hash
    #                 instance_session_data = user_tsession_data.session_data
    #                 data_returning = async_to_sync(telethon_verification_code_sign_in)(phone_number, otp_code, phone_number_hash, instance_session_data)
    #                 session_data = data_returning.get("encrypted_session")
    #                 if session_data is not None:
    #                     user_tsession_data.session_data = session_data
    #                     user_tsession_data.is_verified = True
    #                     user_tsession_data.save()
    #                     return redirect('telegram:contents')
    #                 else:
    #                     user_tsession_data.is_verified = False
    #                     user_tsession_data.save()
    #                     data["messages"] = [
    #                         f"Unsuccessful Verification. The OTP code {otp_code} is not correct.", "Re-enter the OTP code again or Resend Code to get new OTP code"
    #                         ]
    #                     data["msg_need_attention"] = True
                        
    #             else:
    #                 data["messages"] = [
    #                     f"Phone number hash for verification not found.", "Resend code to Try again."]
    #                 data["msg_need_attention"] = True
    #                 hidden_phone_number = (len(phone_number[0:len(phone_number)-4]) * '*') + phone_number[len(phone_number)-4:]
    #                 data["loading_msg"] = f"Resending OTP code to  {hidden_phone_number}"
    #             return render(request, self.template_name, data)
    #         except Exception as e:
    #             err_found = f"Error - {e}"
    #     return render(request, "500.html", context={"exception": err_found})

telegram_user_authentication_view = TelegramUserAuthenticationView.as_view()


@login_required
def get_telegram_otp_code(request):
    # Get the user's Telegram phone number if available
    user_id = request.user.id
    send_otp_code_result = {
        "is_successed": False,
        "messages": "",
        "loading_msg": ""
    }
    try:
        phone_number_object = request.user.telegram_phone_number
        username = request.user.username
        if phone_number_object is not None:
            telegram_phone_number = phone_number_object.as_e164
            hidden_phone_number = (len(telegram_phone_number[0:len(telegram_phone_number)-4]) * '*') + telegram_phone_number[len(telegram_phone_number)-4:]
            data_returning = async_to_sync(telethon_send_code_request)(telegram_phone_number)
            phone_code_hash = data_returning.get("phone_code_hash")
            instance_session_data = data_returning.get("instance_session")
            if phone_code_hash is not None and instance_session_data is not None:
                telegram_session_data = {
                    "telegram_phone_hash": phone_code_hash,
                    "telegram_session_str": instance_session_data.decode()
                }
                send_otp_code_result = {
                    "is_successed": True,
                    "messages": [f"OPT code has been send to {hidden_phone_number}"],
                    "loading_msg" : f"Resending OTP code to  {hidden_phone_number}",
                }
                response = JsonResponse({"data": send_otp_code_result})
                response.set_cookie(
                    f"{username}{telegram_phone_number}",
                    json.dumps(telegram_session_data),
                    httponly=True,  # Prevent JavaScript access
                    # secure=True,  # Send only over HTTPS
                    samesite="Strict",  # Prevent CSRF attacks
                    max_age=432000  # set session age for 5 days
                )
        else:
            send_otp_code_result["messages"] = [f"Failed to send OTP code to {hidden_phone_number}.", "Check if the phone number provided is registered to Telegram"]
            response = JsonResponse({"data": send_otp_code_result})
            response.set_cookie(
                f"{username}{telegram_phone_number}",
                None,
                httponly=True,  # Prevent JavaScript access
                # secure=True,  # Send only over HTTPS
                samesite="Strict",  # Prevent CSRF attacks
                max_age=3  # set session age for 3 seconds
            )
        return response
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        _error = f"Error - {e}"
        print(f">>>> (func) get_telegram_otp_code Error Occur - {_error} <<<<")
        return JsonResponse(
            {"error": _error}, status=500
        )


@login_required
def assign_telegram_entity_contents_fetching_task(request):
    _error = "Failed to assign celery task."
    try:
        user_id = request.user.id
        phone_number_object = request.user.telegram_phone_number
        username = request.user.username
        if phone_number_object is not None:
            telegram_phone_number = phone_number_object.as_e164
            load_user_telegram_session_data_str = request.COOKIES.get(f"{username}{telegram_phone_number}")
            if load_user_telegram_session_data_str is not None:
                load_user_telegram_session_data = json.loads(load_user_telegram_session_data_str)
                telegram_session_str = load_user_telegram_session_data.get("telegram_session_str")
                if telegram_session_str is not None:
                    entity_id = request.POST.get("entity_id")
                    fetch_start_id = int(request.POST.get("min_id"))
                    POST_DATA = request.POST
                    
                    print(f">>>>>> POST Data --- {POST_DATA} <<<<<<<")

                    print(f">>>>>> Entity ID --- {entity_id}({type(entity_id)}) <<<<<<<")

                    # update the user's latest telegram entities info in the background. Target task will only get assign if there's not currently active task is running
                    load_user_telegram_entity_contents_task_id = request.COOKIES.get(f"load_user_telegram_entity_{entity_id}_contents_task_id")
                    if load_user_telegram_entity_contents_task_id is not None:
                        task_result = AsyncResult(load_user_telegram_entity_contents_task_id)
                        if task_result.ready():
                            print(f">>>>> Is Ready - {AsyncResult(load_user_telegram_entity_contents_task_id).ready()}")
                            load_user_telegram_entity_contents_task_id = load_user_telegram_entity_contents.delay(user_id,telegram_session_str.encode(), entity_id, min_content_id=fetch_start_id)
                            
                    else:
                    #   print(f"Min Content id - {fetch_start_id}({type(fetch_start_id)})")
                      print(f"No task id - {load_user_telegram_entity_contents_task_id}")    
                      load_user_telegram_entity_contents_task_id = load_user_telegram_entity_contents.delay(user_id,telegram_session_str.encode(), entity_id, min_content_id=fetch_start_id)

                    print(f">>>> load_user_telegram_entity_contents_task_id - {load_user_telegram_entity_contents_task_id}")
                    response = JsonResponse({'message': 'Task initiated'})
                    response.set_cookie(
                        f"load_user_telegram_entity_{entity_id}_contents_task_id",
                        load_user_telegram_entity_contents_task_id,
                        httponly=True,  # Prevent JavaScript access
                        # secure=True,  # Send only over HTTPS
                        samesite="Strict",  # Prevent CSRF attacks
                        max_age=180  # same as soft_time_limit 180 seconds
                    )
                    return response                    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        _error = f"Error - {e}"
        print(f">>>> (func) fetch_telegram_entity_contents Error Occur - {_error} <<<<")
    return JsonResponse(
        {"error": _error}, status=500
    )

# Just response immediatly user request by data from database
@login_required
def fetch_telegram_entity_contents(request):
    try:  
        page = int(request.POST.get("page", 1))
        per_fetch = DEFAULT_PER_FETCH
        entity_id = request.POST.get("entity_id")
        fetch_type = request.POST.get("fetch_type")
        fetch_start_id = int(request.POST.get("min_id"))
        # get the latest content id that user have downloaded 
        entity_content_rows_data = []
        print(f">>>> FETCH Type - {fetch_type}")
        if fetch_type == "date":
            tz_diff_hrs = int(request.POST.get("timezone_diff_hr"))
            fetch_start_date_str = request.POST.get("start_date")
            fetch_end_date_str = request.POST.get("end_date")
            fetch_start_date_utc = datetime.strptime(fetch_start_date_str, '%Y-%m-%d') + timedelta(hours=tz_diff_hrs)
            end_date_utc = datetime.strptime(fetch_end_date_str, '%Y-%m-%d') + timedelta(hours=tz_diff_hrs)

            # Add one day to the end date to make it exclusive
            fetch_end_date_utc = end_date_utc + timedelta(days=1)

            # pull the user telegram entity contents data from database with dates range filter
            entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id,entity_post_timestamp__gte=fetch_start_date_utc, entity_post_timestamp__lt=fetch_end_date_utc).order_by('content_id')
        elif fetch_type == "id":
            fetch_limit = int(request.POST.get("limit"))
            # fetch_end_id = fetch_start_id + fetch_limit

            # pull the user telegram entity contents data from database with ids range filter
            entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id,content_id__gte=fetch_start_id).order_by("content_id")[:fetch_limit]
            # print(f"entity_content_rows_data - {entity_content_rows_data}")
        else:
            entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id).order_by('-content_id')[:per_fetch] # Get the data in content_id reversed mean newest to oldest,
        
        pull_data = []
        row_N = 0
        for _each in entity_content_rows_data:
            if _each.entity_text_content != "":
                row_N += 1
                post_timestamp = _each.entity_post_timestamp + timedelta(hours=7) # UTC to Bangkok/Asia timezome
                pull_data.append(
                    {
                        "No": row_N,
                        "Content-id": _each.content_id,
                        "Origin-Description": _each.entity_text_content,
                        "Posted-Date": f"{post_timestamp.date()}",
                        "Posted-Time": f"{post_timestamp.time()}",
                        "Time": _each.time_in_text_content,
                        "Date": _each.date_in_text_content,
                        "Description": _each.processed_text_content,
                        "Source-Link": _each.entity_content_url,
                    }
                )
        
        paginator = Paginator(pull_data, per_fetch)
        page_obj = paginator.get_page(page)
        # print(f">>>>>>> Pull Data ----- {pull_data} <<<<<<<<")
        response = JsonResponse({
            # "user_id": user_id,
            "entity_id": entity_id,
            "data": list(page_obj),
            "columns": list(pull_data[0].keys()) if pull_data else [],
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "page": page_obj.number,
            "total_pages": paginator.num_pages
        })
        return response
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        _error = f"Error - {e}"
        print(f">>>> (func) fetch_telegram_entity_contents Error Occur - {_error} <<<<")
        return JsonResponse(
            {"error": _error}, status=500
        )


# This endpoint combined both celery task assigning and data loading and returning from database for the reqeust
@login_required
def fetch_telegram_entity_contents_COMBINE(request):
    _error = "Invalid Request"
    try:
        user_id = request.user.id
        phone_number_object = request.user.telegram_phone_number
        username = request.user.username
        if phone_number_object is not None:
            telegram_phone_number = phone_number_object.as_e164
            load_user_telegram_session_data_str = request.COOKIES.get(f"{username}{telegram_phone_number}")
            if load_user_telegram_session_data_str is not None:
                load_user_telegram_session_data = json.loads(load_user_telegram_session_data_str)
                telegram_session_str = load_user_telegram_session_data.get("telegram_session_str")
                if telegram_session_str is not None:
                    page = int(request.POST.get("page", 1))
                    per_fetch = DEFAULT_PER_FETCH
                    entity_id = request.POST.get("entity_id")
                    fetch_type = request.POST.get("fetch_type")
                    fetch_start_id = int(request.POST.get("min_id"))
                    POST_DATA = request.POST

                    print(f">>>>>> POST Data --- {POST_DATA} <<<<<<<")

                    print(f">>>>>> Entity ID --- {entity_id}({type(entity_id)}) <<<<<<<")

                    # update the user's latest telegram entities info in the background. Target task will only get assign if there's not currently active task is running
                    load_user_telegram_entity_contents_task_id = request.COOKIES.get(f"load_user_telegram_entity_{entity_id}_contents_task_id")
                    if load_user_telegram_entity_contents_task_id is not None:
                        task_result = AsyncResult(load_user_telegram_entity_contents_task_id)
                        if task_result.ready():
                            print(f">>>>> Is Ready - {AsyncResult(load_user_telegram_entity_contents_task_id).ready()}")
                            load_user_telegram_entity_contents_task_id = load_user_telegram_entity_contents.delay(user_id,telegram_session_str.encode(), entity_id, min_content_id=fetch_start_id)
                            
                    else:
                    #   print(f"Min Content id - {fetch_start_id}({type(fetch_start_id)})")
                      print(f"No task id - {load_user_telegram_entity_contents_task_id}")    
                      load_user_telegram_entity_contents_task_id = load_user_telegram_entity_contents.delay(user_id,telegram_session_str.encode(), entity_id, min_content_id=fetch_start_id)

                    print(f">>>> load_user_telegram_entity_contents_task_id - {load_user_telegram_entity_contents_task_id}")
                    
                    # get the latest content id that user have downloaded 
                    user_telegram_entity_data = TelegramUserEntity.objects.filter(telegram_entity_id=entity_id, user_id=user_id).first()
                    if user_telegram_entity_data is not None:
                        entity_content_rows_data = []
                        print(f">>>> FETCH Type - {fetch_type}")
                        if fetch_type == "date":
                            tz_diff_hrs = int(request.POST.get("timezone_diff_hr"))
                            fetch_start_date_str = request.POST.get("start_date")
                            fetch_end_date_str = request.POST.get("end_date")
                            fetch_start_date_utc = datetime.strptime(fetch_start_date_str, '%Y-%m-%d') + timedelta(hours=tz_diff_hrs)
                            end_date_utc = datetime.strptime(fetch_end_date_str, '%Y-%m-%d') + timedelta(hours=tz_diff_hrs)

                            # Add one day to the end date to make it exclusive
                            fetch_end_date_utc = end_date_utc + timedelta(days=1)

                            # pull the user telegram entity contents data from database with dates range filter
                            entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id,entity_post_timestamp__gte=fetch_start_date_utc, entity_post_timestamp__lt=fetch_end_date_utc).order_by('content_id')
                        elif fetch_type == "id":
                            fetch_limit = int(request.POST.get("limit"))
                            fetch_end_id = fetch_start_id + fetch_limit

                            # pull the user telegram entity contents data from database with ids range filter
                            entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id,content_id__gte=fetch_start_id, content_id__lt=fetch_end_id)
                            # print(f"entity_content_rows_data - {entity_content_rows_data}")
                        else:
                            if user_telegram_entity_data.latest_downloaded_content is not None:
                                latest_downloaded_content_id = user_telegram_entity_data.latest_downloaded_content.id
                                # pull the current available user telegram entity contents data from database using id start filter
                                entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id,id__gte=latest_downloaded_content_id)
                            else:
                                entity_content_rows_data = TelegramEntityContentData.objects.filter(telegram_entity_id=entity_id).order_by('-content_id')[:per_fetch] # Get the data in content_id reversed mean newest to oldest,
                        
                        pull_data = []
                        row_N = 0
                        for _each in entity_content_rows_data:
                            row_N += 1
                            post_timestamp = _each.entity_post_timestamp + timedelta(hours=7) # UTC to Bangkok/Asia timezome
                            pull_data.append(
                                {
                                    "No": row_N,
                                    "Content-id": _each.content_id,
                                    "Origin-Description": _each.entity_text_content,
                                    "Posted-Date": f"{post_timestamp.date()}",
                                    "Posted-Time": f"{post_timestamp.time()}",
                                    "Description": _each.processed_text_content,
                                    "Time": _each.time_in_text_content,
                                    "Date": _each.date_in_text_content,
                                    "Source-Link": _each.entity_content_url,
                                }
                            )
                        
                        paginator = Paginator(pull_data, per_fetch)
                        page_obj = paginator.get_page(page)
                        # print(f">>>>>>> Pull Data ----- {pull_data} <<<<<<<<")
                        response = JsonResponse({
                            # "user_id": user_id,
                            "entity_id": entity_id,
                            "data": list(page_obj),
                            "columns": list(pull_data[0].keys()) if pull_data else [],
                            "has_next": page_obj.has_next(),
                            "has_previous": page_obj.has_previous(),
                            "page": page_obj.number,
                            "total_pages": paginator.num_pages
                        })
                        response.set_cookie(
                            f"load_user_telegram_entity_{entity_id}_contents_task_id",
                            load_user_telegram_entity_contents_task_id,
                            httponly=True,  # Prevent JavaScript access
                            # secure=True,  # Send only over HTTPS
                            samesite="Strict",  # Prevent CSRF attacks
                            max_age=180  # same as soft_time_limit 180 seconds
                        )
                        return response
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        _error = f"Error - {e}"
        print(f">>>> (func) fetch_telegram_entity_contents Error Occur - {_error} <<<<")
    return JsonResponse(
        {"error": _error}, status=500
    )


# JSON endpoint to return paginated data
@login_required
def update_telegram_entity_contents(request):   
    try:
        user_id = request.user.id
        phone_number_object = request.user.telegram_phone_number
        username = request.user.username
        if phone_number_object is not None:
            telegram_phone_number = phone_number_object.as_e164
            load_user_telegram_session_data_str = request.COOKIES.get(f"{username}{telegram_phone_number}")
            if load_user_telegram_session_data_str is not None:
                load_user_telegram_session_data = json.loads(load_user_telegram_session_data_str)
                telegram_session_str = load_user_telegram_session_data.get("telegram_session_str")
                if telegram_session_str is not None:
                    content_id = int(request.POST.get("content_id",0))
                    per_fetch = int(request.POST.get("per_fetch", 5))
                    entity_id = request.POST.get("entity_id")
                    POST_DATA = request.POST

                    print(f">>>>>> POST Data --- {POST_DATA} <<<<<<<")
                    # raise Exception("testing")

                    if user_id and (content_id > 0):
                        entity_content_data = TelegramEntityContentData.objects.filter(content_id=content_id).first()
                        if entity_content_data is not None:
                            extracted_text = request.POST.get("extracted_text")
                            extracted_date = request.POST.get("extracted_date")
                            extracted_time = request.POST.get("extracted_time")
                            entity_content_data.processed_text_content = extracted_text
                            entity_content_data.date_in_text_content = extracted_date
                            entity_content_data.time_in_text_content = extracted_time
                            entity_content_data.updated_by_id = user_id
                            entity_content_data.save()
                            update_info = {"status_msg": "Data updated successful."}
                        else:
                            update_info = {"status_msg": "Data update failed. Row not found."}
                        return JsonResponse(update_info)
        update_info = {"status_msg": "Invalid Data. Update Failed"}
        return JsonResponse(update_info)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        _error = f"Error - {e}"
        print(f">>>> (func) update_telegram_entity_contents Error Occur - {_error} <<<<")
        return JsonResponse(
            {"error": _error}, status=500
        )