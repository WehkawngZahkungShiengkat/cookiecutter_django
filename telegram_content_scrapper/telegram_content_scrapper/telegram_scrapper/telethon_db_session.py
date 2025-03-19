# from telethon.sessions import StringSession
# from telegram_content_scrapper.telegram_scrapper.models import TelethonSession

# class DjangoTelethonSession(StringSession):
#     def __init__(self, session_name, *args, **kwargs):
#         self.session_name = session_name
#         try:
#             #Try to load an existing session from database
#             session_obj = TelethonSession.objects.get(session_name=session_name)
#             session_string = session_obj.session_data.decode() # Convert bytes to string
#         except TelethonSession.DoesNotExist:
#             session_string = None # No existing session, start fresh

#         super().__init__(session_string, *args, **kwargs)

#     def save(self):
#         """Save the session to the database"""
#         session_string = self.save_string()
#         session_obj, created = TelethonSession.objects.update_or_create(
#             session_name=self.session_name,
#             defaults={"session_data": session_string.encode()} #Covert string to bytes
#         ) 

from telethon.sessions.memory import MemorySession
from telethon.crypto import AuthKey
from django.utils import timezone
from telegram_content_scrapper.telegram_scrapper.models import TelethonSession

class DjangoSession(MemorySession):
    def __init__(self, session_name):
        super().__init__()
        self.session_name = session_name
        self._load_session()

    def _load_session(self):
        # Try to load the session from database
        try:
            session = TelethonSession.objects.get(session_name=self.session_name)
            self._dc_id = session.dc_id
            self._server_address = session.server_address
            self._port = session.port
            self._auth_key = AuthKey(session.auth_key) if session.auth_key else None
        except TelethonSession.DoesNotExist:
            # Create new session if it doesn't exist
            session = TelethonSession.objects.create(
                session_name=self.session_name
            )

    def clone(self, to_instance=None):
        cloned = super().clone(to_instance)
        cloned.session_name = self.session_name
        return cloned

    def set_dc(self, dc_id, server_address, port):
        super().set_dc(dc_id, server_address, port)
        TelethonSession.objects.filter(session_name=self.session_name).update(
            dc_id=dc_id,
            server_address=server_address,
            port=port
        )

    def auth_key(self, value=None):
        if value:
            self._auth_key = value
            TelethonSession.objects.filter(session_name=self.session_name).update(
                auth_key=value.key
            )
        return self._auth_key

    def get_update_state(self, entity_id):
        return None

    def set_update_state(self, entity_id, state):
        pass

    def save(self):
        # Ensure the session exists
        session, _ = TelethonSession.objects.get_or_create(
            session_name=self.session_name
        )
        
        # Update the session data
        session.dc_id = self._dc_id
        session.server_address = self._server_address
        session.port = self._port
        session.auth_key = self._auth_key.key if self._auth_key else None
        session.save()

    def close(self):
        pass

    def delete(self):
        TelethonSession.objects.filter(session_name=self.session_name).delete()

    # Entity processing methods
    def process_entities(self, tlo):
        rows = self._entities_to_rows(tlo)
        if not rows:
            return

        # Delete previous mapping
        TelethonEntityMapping.objects.filter(
            session__session_name=self.session_name,
            id__in=[row[0] for row in rows]
        ).delete()

        # Insert new mapping
        TelethonEntityMapping.objects.bulk_create([
            TelethonEntityMapping(
                session_id=TelethonSession.objects.get(session_name=self.session_name).id,
                id=row[0],
                hash=row[1],
                username=row[2],
                phone=row[3],
                date=timezone.now()
            )
            for row in rows
        ])

    def get_entity_rows_by_phone(self, phone):
        try:
            entry = TelethonEntityMapping.objects.get(
                session__session_name=self.session_name,
                phone=phone
            )
            return (entry.id, entry.hash)
        except TelethonEntityMapping.DoesNotExist:
            return None

    def get_entity_rows_by_username(self, username):
        try:
            entry = TelethonEntityMapping.objects.get(
                session__session_name=self.session_name,
                username=username
            )
            return (entry.id, entry.hash)
        except TelethonEntityMapping.DoesNotExist:
            return None

    def get_entity_rows_by_id(self, id, exact=True):
        try:
            entry = TelethonEntityMapping.objects.get(
                session__session_name=self.session_name,
                id=id
            )
            return (entry.id, entry.hash)
        except TelethonEntityMapping.DoesNotExist:
            return None
