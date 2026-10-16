import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Default [FirebaseOptions] for use with Firebase apps.
/// Configured using `google-services.json` for package `com.kuru.app.kuru_app`.
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        return android;
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyC2I_hNs1-0B3yf38KdXlsdNJuSfQj6Kzc',
    appId: '1:784894558707:android:aab3c36d3b5f5ac37e9286',
    messagingSenderId: '784894558707',
    projectId: 'career-ba46c',
    storageBucket: 'career-ba46c.firebasestorage.app',
  );

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyC2I_hNs1-0B3yf38KdXlsdNJuSfQj6Kzc',
    appId: '1:784894558707:web:aab3c36d3b5f5ac37e9286',
    messagingSenderId: '784894558707',
    projectId: 'career-ba46c',
    storageBucket: 'career-ba46c.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyC2I_hNs1-0B3yf38KdXlsdNJuSfQj6Kzc',
    appId: '1:784894558707:ios:aab3c36d3b5f5ac37e9286',
    messagingSenderId: '784894558707',
    projectId: 'career-ba46c',
    storageBucket: 'career-ba46c.firebasestorage.app',
    iosBundleId: 'com.kuru.app.kuruApp',
  );
}
