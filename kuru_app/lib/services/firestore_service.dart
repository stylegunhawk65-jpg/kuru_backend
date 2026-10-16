import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import '../core/api/api_client.dart';
import '../models/career_note.dart';
import 'auth_service.dart';

/// Cloud Firestore Service managing user-isolated settings, preferences, and study notes.
/// Strictly enforces per-user scoping under `users/{uid}/...`.
class FirestoreService {
  final AuthService _authService;
  final FirebaseFirestore? _firestore;

  // In-memory fallback cache for testing / offline environments without native binary plugins
  final Map<String, Map<String, dynamic>> _memoryPreferences = {};
  final Map<String, List<CareerNote>> _memoryNotes = {};
  final Map<String, StreamController<Map<String, dynamic>>> _prefControllers = {};
  final Map<String, StreamController<List<CareerNote>>> _notesControllers = {};

  FirestoreService({
    required AuthService authService,
    FirebaseFirestore? firestore,
  })  : _authService = authService,
        _firestore = firestore;

  FirebaseFirestore? get _client {
    if (_firestore != null) return _firestore;
    try {
      return FirebaseFirestore.instance;
    } catch (_) {
      return null;
    }
  }

  String _requireAuthenticatedUid([String? targetUid]) {
    final currentUid = _authService.currentUid;
    if (currentUid == null || currentUid.isEmpty) {
      throw const AuthExpiredException('Authentication required for Cloud Firestore access.');
    }
    if (targetUid != null && targetUid != currentUid) {
      throw const AuthExpiredException('Cross-user Firestore access denied.');
    }
    return currentUid;
  }

  // ---------------------------------------------------------------------------
  // User Preferences
  // ---------------------------------------------------------------------------

  Future<void> saveUserPreferences(Map<String, dynamic> preferences, {String? targetUid}) async {
    final uid = _requireAuthenticatedUid(targetUid);
    final data = Map<String, dynamic>.from(preferences);
    data['updated_at'] = DateTime.now().toIso8601String();
    data['uid'] = uid;

    final client = _client;
    if (client != null) {
      try {
        await client
            .collection('users')
            .doc(uid)
            .collection('settings')
            .doc('preferences')
            .set(data, SetOptions(merge: true));
        return;
      } catch (e) {
        debugPrint('Firestore saveUserPreferences fallback to memory cache: $e');
      }
    }

    final existing = _memoryPreferences.putIfAbsent(uid, () => {});
    existing.addAll(data);
    _prefControllers[uid]?.add(Map<String, dynamic>.from(existing));
  }

  Future<Map<String, dynamic>> getUserPreferences({String? targetUid}) async {
    final uid = _requireAuthenticatedUid(targetUid);

    final client = _client;
    if (client != null) {
      try {
        final doc = await client
            .collection('users')
            .doc(uid)
            .collection('settings')
            .doc('preferences')
            .get();
        if (doc.exists && doc.data() != null) {
          return doc.data()!;
        }
        return {};
      } catch (e) {
        debugPrint('Firestore getUserPreferences fallback to memory cache: $e');
      }
    }

    return Map<String, dynamic>.from(_memoryPreferences[uid] ?? {});
  }

  Stream<Map<String, dynamic>> userPreferencesStream({String? targetUid}) {
    final uid = _requireAuthenticatedUid(targetUid);

    final client = _client;
    if (client != null) {
      try {
        return client
            .collection('users')
            .doc(uid)
            .collection('settings')
            .doc('preferences')
            .snapshots()
            .map((snapshot) => snapshot.data() ?? {});
      } catch (e) {
        debugPrint('Firestore stream fallback to memory stream: $e');
      }
    }

    final controller = _prefControllers.putIfAbsent(
      uid,
      () => StreamController<Map<String, dynamic>>.broadcast(),
    );
    // Send immediate initial value
    Future.microtask(() {
      controller.add(Map<String, dynamic>.from(_memoryPreferences[uid] ?? {}));
    });
    return controller.stream;
  }

  // ---------------------------------------------------------------------------
  // Career Notes (Personal Study / Interview Notes)
  // ---------------------------------------------------------------------------

  Future<CareerNote> addCareerNote({
    required String title,
    required String content,
    List<String> tags = const [],
    String? targetUid,
  }) async {
    final uid = _requireAuthenticatedUid(targetUid);
    final now = DateTime.now();

    final client = _client;
    if (client != null) {
      try {
        final docRef = await client
            .collection('users')
            .doc(uid)
            .collection('career_notes')
            .add({
          'uid': uid,
          'title': title,
          'content': content,
          'tags': tags,
          'created_at': now.toIso8601String(),
          'updated_at': now.toIso8601String(),
        });

        return CareerNote(
          id: docRef.id,
          uid: uid,
          title: title,
          content: content,
          tags: tags,
          createdAt: now,
          updatedAt: now,
        );
      } catch (e) {
        debugPrint('Firestore addCareerNote fallback to memory cache: $e');
      }
    }

    final note = CareerNote(
      id: 'note_${DateTime.now().millisecondsSinceEpoch}',
      uid: uid,
      title: title,
      content: content,
      tags: tags,
      createdAt: now,
      updatedAt: now,
    );

    final notes = _memoryNotes.putIfAbsent(uid, () => []);
    notes.insert(0, note);
    _notesControllers[uid]?.add(List<CareerNote>.from(notes));
    return note;
  }

  Stream<List<CareerNote>> getCareerNotesStream({String? targetUid}) {
    final uid = _requireAuthenticatedUid(targetUid);

    final client = _client;
    if (client != null) {
      try {
        return client
            .collection('users')
            .doc(uid)
            .collection('career_notes')
            .orderBy('created_at', descending: true)
            .snapshots()
            .map((snapshot) {
          return snapshot.docs.map((doc) => CareerNote.fromJson(doc.data(), doc.id)).toList();
        });
      } catch (e) {
        debugPrint('Firestore notes stream fallback to memory stream: $e');
      }
    }

    final controller = _notesControllers.putIfAbsent(
      uid,
      () => StreamController<List<CareerNote>>.broadcast(),
    );
    Future.microtask(() {
      controller.add(List<CareerNote>.from(_memoryNotes[uid] ?? []));
    });
    return controller.stream;
  }

  Future<void> deleteCareerNote(String noteId, {String? targetUid}) async {
    final uid = _requireAuthenticatedUid(targetUid);

    final client = _client;
    if (client != null) {
      try {
        await client
            .collection('users')
            .doc(uid)
            .collection('career_notes')
            .doc(noteId)
            .delete();
        return;
      } catch (e) {
        debugPrint('Firestore deleteCareerNote fallback to memory cache: $e');
      }
    }

    final notes = _memoryNotes[uid] ?? [];
    notes.removeWhere((n) => n.id == noteId);
    _notesControllers[uid]?.add(List<CareerNote>.from(notes));
  }
}
