import 'package:flutter_test/flutter_test.dart';
import 'package:kuru_app/core/api/api_client.dart';
import 'package:kuru_app/core/storage/token_storage.dart';
import 'package:kuru_app/services/auth_service.dart';
import 'package:kuru_app/services/firestore_service.dart';

void main() {
  group('Firebase Authentication & Token Lifecycle Tests', () {
    late TokenStorage storage;
    late AuthService authService;

    setUp(() async {
      storage = TokenStorage.isolated();
      await storage.clearCredentials();
      authService = AuthService(storage: storage);
    });

    test('Initial auth state is unauthenticated when token storage is empty', () {
      expect(authService.isAuthenticated, isFalse);
      expect(authService.status, equals(AuthStatus.unauthenticated));
      expect(authService.currentUid, isNull);
    });

    test('signUpWithEmailAndPassword establishes authenticated session and stores credentials', () async {
      await authService.signUpWithEmailAndPassword(
        email: 'newstudent@kuru.ai',
        password: 'SecurePassword123!',
      );

      expect(authService.isAuthenticated, isTrue);
      expect(authService.status, equals(AuthStatus.authenticated));
      expect(authService.currentEmail, equals('newstudent@kuru.ai'));
      expect(storage.hasToken, isTrue);
      expect(storage.token, isNotNull);
    });

    test('signInWithEmailAndPassword persists token and broadcasts authenticated status', () async {
      await authService.signInWithEmailAndPassword(
        email: 'returningstudent@kuru.ai',
        password: 'Password987!',
      );

      expect(authService.isAuthenticated, isTrue);
      expect(authService.currentEmail, equals('returningstudent@kuru.ai'));
      expect(storage.token, isNotEmpty);
    });

    test('signOut terminates session, clears token storage, and updates status', () async {
      await authService.signInWithDevSession(uid: 'student_alpha', email: 'alpha@kuru.ai');
      expect(authService.isAuthenticated, isTrue);

      await authService.signOut();
      expect(authService.isAuthenticated, isFalse);
      expect(authService.status, equals(AuthStatus.unauthenticated));
      expect(storage.hasToken, isFalse);
    });

    test('getIdToken returns fresh token and keeps storage synchronized', () async {
      await authService.signInWithToken(
        firebaseIdToken: 'initial_token_abc',
        uid: 'user_123',
        email: 'test@kuru.ai',
      );

      final token = await authService.getIdToken();
      expect(token, equals('initial_token_abc'));
      expect(storage.token, equals('initial_token_abc'));
    });
  });

  group('Cloud Firestore User Isolation & Storage Tests', () {
    late TokenStorage storageA;
    late TokenStorage storageB;
    late AuthService authServiceA;
    late AuthService authServiceB;
    late FirestoreService firestoreA;
    late FirestoreService firestoreB;

    setUp(() async {
      storageA = TokenStorage.isolated();
      storageB = TokenStorage.isolated();
      await storageA.clearCredentials();
      await storageB.clearCredentials();

      authServiceA = AuthService(storage: storageA);
      authServiceB = AuthService(storage: storageB);

      await authServiceA.signInWithDevSession(uid: 'usr_student_alpha', email: 'alpha@kuru.ai');
      await authServiceB.signInWithDevSession(uid: 'usr_student_bravo', email: 'bravo@kuru.ai');

      firestoreA = FirestoreService(authService: authServiceA);
      firestoreB = FirestoreService(authService: authServiceB);
    });

    test('saveUserPreferences and getUserPreferences persist per-user data', () async {
      await firestoreA.saveUserPreferences({
        'weekly_study_goal_hours': 15,
        'preferred_role': 'Backend Engineer',
        'notifications_enabled': true,
      });

      final prefsA = await firestoreA.getUserPreferences();
      expect(prefsA['weekly_study_goal_hours'], equals(15));
      expect(prefsA['preferred_role'], equals('Backend Engineer'));
      expect(prefsA['uid'], equals('usr_student_alpha'));

      // User B has empty preferences initially
      final prefsB = await firestoreB.getUserPreferences();
      expect(prefsB['weekly_study_goal_hours'], isNull);
    });

    test('Career Notes CRUD operations are strictly user-isolated', () async {
      // 1. User A adds a career study note
      final noteA = await firestoreA.addCareerNote(
        title: 'System Design: Distributed Caching',
        content: 'Use Redis cluster with write-through cache pattern.',
        tags: ['redis', 'caching', 'system-design'],
      );

      expect(noteA.id, isNotEmpty);
      expect(noteA.uid, equals('usr_student_alpha'));
      expect(noteA.title, equals('System Design: Distributed Caching'));

      // 2. User A notes stream contains noteA
      final notesStreamA = firestoreA.getCareerNotesStream();
      final userANotes = await notesStreamA.first;
      expect(userANotes.length, equals(1));
      expect(userANotes.first.title, equals('System Design: Distributed Caching'));

      // 3. User B notes stream does NOT contain User A note (Strict Isolation)
      final notesStreamB = firestoreB.getCareerNotesStream();
      final userBNotes = await notesStreamB.first;
      expect(userBNotes.isEmpty, isTrue);

      // 4. User A deletes note
      await firestoreA.deleteCareerNote(noteA.id);
      final notesAfterDelete = await firestoreA.getCareerNotesStream().first;
      expect(notesAfterDelete.isEmpty, isTrue);
    });

    test('Cross-user access attempt explicitly throws AuthExpiredException', () async {
      // User A attempts to read User B's Firestore document
      expect(
        firestoreA.getUserPreferences(targetUid: 'usr_student_bravo'),
        throwsA(isA<AuthExpiredException>()),
      );

      // User B attempts to write to User A's path
      expect(
        firestoreB.saveUserPreferences(
          {'malicious_entry': true},
          targetUid: 'usr_student_alpha',
        ),
        throwsA(isA<AuthExpiredException>()),
      );
    });

    test('Unauthenticated user cannot read or write Firestore', () async {
      final unauthStorage = TokenStorage.isolated();
      await unauthStorage.clearCredentials();
      final unauthService = AuthService(storage: unauthStorage);
      final unauthFirestore = FirestoreService(authService: unauthService);

      expect(
        unauthFirestore.getUserPreferences(),
        throwsA(isA<AuthExpiredException>()),
      );
      expect(
        unauthFirestore.addCareerNote(title: 'Fail', content: 'Should not save'),
        throwsA(isA<AuthExpiredException>()),
      );
    });
  });
}
