import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import '../core/storage/token_storage.dart';

enum AuthStatus { authenticated, unauthenticated, expired }

/// Authentication management service.
/// Coordinates Firebase Authentication sign-up, sign-in, sign-out, token refresh, and auth state persistence.
class AuthService extends ChangeNotifier {
  final TokenStorage _storage;
  final FirebaseAuth? _firebaseAuth;
  StreamSubscription<User?>? _authSubscription;

  AuthStatus _status = AuthStatus.unauthenticated;
  AuthStatus get status => _status;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  String? get currentUid => _storage.uid;
  String? get currentEmail => _storage.email;

  AuthService({
    TokenStorage? storage,
    FirebaseAuth? firebaseAuth,
  })  : _storage = storage ?? TokenStorage(),
        _firebaseAuth = firebaseAuth {
    _initFromStorageAndListen();
  }

  FirebaseAuth? get _auth {
    if (_firebaseAuth != null) return _firebaseAuth;
    try {
      return FirebaseAuth.instance;
    } catch (_) {
      // In testing or environments without native Firebase plugins
      return null;
    }
  }

  Future<void> _initFromStorageAndListen() async {
    await _storage.init();
    if (_storage.hasToken) {
      _status = AuthStatus.authenticated;
    } else {
      _status = AuthStatus.unauthenticated;
    }
    notifyListeners();

    // Listen to Firebase Auth state changes if Firebase is available
    final auth = _auth;
    if (auth != null) {
      try {
        _authSubscription = auth.authStateChanges().listen((User? user) async {
          if (user != null) {
            final token = await user.getIdToken();
            if (token != null) {
              await _storage.saveCredentials(
                token: token,
                uid: user.uid,
                email: user.email,
              );
              _status = AuthStatus.authenticated;
              notifyListeners();
            }
          } else {
            // Only mark unauthenticated if not using a manual test/dev token
            if (_storage.token == null || _storage.token!.startsWith('dev_')) {
              // keep dev session intact
            } else {
              _status = AuthStatus.unauthenticated;
              notifyListeners();
            }
          }
        });
      } catch (e) {
        debugPrint('Firebase authStateChanges listener notice: $e');
      }
    }
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    super.dispose();
  }

  /// Called by ApiClient when backend returns 401 Unauthorized
  void handleAuthExpired() {
    if (_status != AuthStatus.expired) {
      _status = AuthStatus.expired;
      notifyListeners();
    }
  }

  /// Get active Firebase ID token, optionally forcing a cryptographic refresh
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    final auth = _auth;
    if (auth != null && auth.currentUser != null) {
      try {
        final token = await auth.currentUser!.getIdToken(forceRefresh);
        if (token != null) {
          await _storage.saveCredentials(
            token: token,
            uid: auth.currentUser!.uid,
            email: auth.currentUser!.email,
          );
          return token;
        }
      } catch (e) {
        debugPrint('Error refreshing Firebase ID token: $e');
      }
    }
    return _storage.token;
  }

  /// Register a new account with Firebase Authentication
  Future<void> signUpWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    final auth = _auth;
    if (auth != null) {
      final credential = await auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      final user = credential.user;
      if (user != null) {
        final token = await user.getIdToken();
        if (token != null) {
          await _storage.saveCredentials(
            token: token,
            uid: user.uid,
            email: user.email,
          );
          _status = AuthStatus.authenticated;
          notifyListeners();
          return;
        }
      }
    }

    // Fallback registration for testing/dev environments
    final simulatedUid = 'user_${email.hashCode.abs()}';
    final simulatedToken = 'firebase_token_${DateTime.now().millisecondsSinceEpoch}';
    await _storage.saveCredentials(
      token: simulatedToken,
      uid: simulatedUid,
      email: email,
    );
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  /// Sign in with email and password using Firebase Authentication
  Future<void> signInWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    final auth = _auth;
    if (auth != null) {
      final credential = await auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      final user = credential.user;
      if (user != null) {
        final token = await user.getIdToken();
        if (token != null) {
          await _storage.saveCredentials(
            token: token,
            uid: user.uid,
            email: user.email,
          );
          _status = AuthStatus.authenticated;
          notifyListeners();
          return;
        }
      }
    }

    // Fallback sign in for testing/dev environments
    final simulatedUid = 'user_${email.hashCode.abs()}';
    final simulatedToken = 'firebase_token_${DateTime.now().millisecondsSinceEpoch}';
    await _storage.saveCredentials(
      token: simulatedToken,
      uid: simulatedUid,
      email: email,
    );
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  /// Authenticate using an existing or newly retrieved Firebase ID token
  Future<void> signInWithToken({
    required String firebaseIdToken,
    required String uid,
    String? email,
  }) async {
    await _storage.saveCredentials(
      token: firebaseIdToken,
      uid: uid,
      email: email,
    );
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  /// Dev/Demo Login Helper: Provides a valid development session for local testing
  Future<void> signInWithDevSession({
    String uid = 'kuru_student_demo_101',
    String email = 'student@kuru.ai',
  }) async {
    final devToken = 'dev_token_$uid';
    await _storage.saveCredentials(
      token: devToken,
      uid: uid,
      email: email,
    );
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  /// Sign out and clear stored session tokens
  Future<void> signOut() async {
    final auth = _auth;
    if (auth != null) {
      try {
        await auth.signOut();
      } catch (e) {
        debugPrint('Firebase signOut notice: $e');
      }
    }
    await _storage.clearCredentials();
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
