"""Cloud Firestore integration service for user-isolated mobile preferences and real-time data."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid
import firebase_admin
from firebase_admin import firestore

from app.core.auth import initialize_firebase
from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger("kuru.firestore")


class FirestoreAccessDenied(AppException):
    """Raised when cross-user or unauthorized Firestore access is attempted."""

    def __init__(self, detail: str = "Access denied to requested Firestore resource."):
        super().__init__(detail=detail, status_code=403, error_code="FIRESTORE_ACCESS_DENIED")


class FirestoreService:
    """Service providing user-isolated document operations on Cloud Firestore."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        # In-memory storage for test/degraded mode when live credentials are not active
        self._memory_store: dict[str, dict[str, Any]] = {}

    @property
    def client(self) -> Any | None:
        """Lazily initialize and return the Firestore client."""
        if self._client is not None:
            return self._client

        app = initialize_firebase()
        if app is not None:
            try:
                self._client = firestore.client(app=app)
                return self._client
            except Exception as exc:
                logger.warning("Could not initialize live Firestore client: %s", exc)
        return None

    def _ensure_user_match(self, authenticated_uid: str, target_uid: str) -> None:
        """Strict authorization gate: users can only access their own Firestore documents."""
        if not authenticated_uid or authenticated_uid != target_uid:
            raise FirestoreAccessDenied(
                f"Cross-user access denied. Authenticated user '{authenticated_uid}' cannot access user '{target_uid}'."
            )

    async def get_user_preferences(
        self,
        authenticated_uid: str,
        target_uid: str,
    ) -> dict[str, Any]:
        """Fetch mobile/user preferences stored in Firestore. User-isolated."""
        self._ensure_user_match(authenticated_uid, target_uid)

        c = self.client
        if c is not None:
            try:
                doc_ref = c.collection("users").document(target_uid).collection("settings").document("preferences")
                snapshot = doc_ref.get()
                if snapshot.exists:
                    return snapshot.to_dict() or {}
                return {}
            except Exception as exc:
                logger.warning("Live Firestore read failed, falling back to cache: %s", exc)

        user_prefs_key = f"{target_uid}:preferences"
        return self._memory_store.get(user_prefs_key, {})

    async def set_user_preferences(
        self,
        authenticated_uid: str,
        target_uid: str,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        """Set or merge mobile/user preferences stored in Firestore. User-isolated."""
        self._ensure_user_match(authenticated_uid, target_uid)

        data = dict(preferences)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data["firebase_uid"] = target_uid

        c = self.client
        if c is not None:
            try:
                doc_ref = c.collection("users").document(target_uid).collection("settings").document("preferences")
                doc_ref.set(data, merge=True)
                return data
            except Exception as exc:
                logger.warning("Live Firestore write failed, writing to fallback cache: %s", exc)

        user_prefs_key = f"{target_uid}:preferences"
        existing = self._memory_store.get(user_prefs_key, {})
        existing.update(data)
        self._memory_store[user_prefs_key] = existing
        return existing

    async def list_user_notes(
        self,
        authenticated_uid: str,
        target_uid: str,
    ) -> list[dict[str, Any]]:
        """List personal career notes stored in Firestore. User-isolated."""
        self._ensure_user_match(authenticated_uid, target_uid)

        c = self.client
        if c is not None:
            try:
                notes_ref = c.collection("users").document(target_uid).collection("career_notes")
                docs = notes_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
                notes = []
                for d in docs:
                    item = d.to_dict()
                    item["id"] = d.id
                    notes.append(item)
                return notes
            except Exception as exc:
                logger.warning("Live Firestore notes query failed: %s", exc)

        user_notes_key = f"{target_uid}:notes"
        return sorted(
            self._memory_store.get(user_notes_key, []),
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

    async def create_user_note(
        self,
        authenticated_uid: str,
        target_uid: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a personal career note in Firestore. User-isolated."""
        self._ensure_user_match(authenticated_uid, target_uid)

        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        note_data: dict[str, Any] = {
            "id": note_id,
            "firebase_uid": target_uid,
            "title": title,
            "content": content,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }

        c = self.client
        if c is not None:
            try:
                c.collection("users").document(target_uid).collection("career_notes").document(note_id).set(note_data)
                return note_data
            except Exception as exc:
                logger.warning("Live Firestore note creation failed: %s", exc)

        user_notes_key = f"{target_uid}:notes"
        notes = self._memory_store.setdefault(user_notes_key, [])
        notes.append(note_data)
        return note_data

    async def delete_user_note(
        self,
        authenticated_uid: str,
        target_uid: str,
        note_id: str,
    ) -> bool:
        """Delete a personal career note from Firestore. User-isolated."""
        self._ensure_user_match(authenticated_uid, target_uid)

        c = self.client
        if c is not None:
            try:
                c.collection("users").document(target_uid).collection("career_notes").document(note_id).delete()
                return True
            except Exception as exc:
                logger.warning("Live Firestore note deletion failed: %s", exc)

        user_notes_key = f"{target_uid}:notes"
        notes = self._memory_store.get(user_notes_key, [])
        initial_len = len(notes)
        self._memory_store[user_notes_key] = [n for n in notes if n.get("id") != note_id]
        return len(self._memory_store[user_notes_key]) < initial_len


firestore_service = FirestoreService()
