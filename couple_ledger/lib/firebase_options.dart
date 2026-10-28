import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Firebase 프로젝트 wallet-ad6ea 설정.
/// (클라이언트 API 키는 비밀이 아니며, 접근 제어는 Firestore 보안 규칙이 담당한다.)
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError('이 플랫폼은 지원하지 않습니다.');
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyCLyvcVcCx7UF7Lotx1j13Ei6-UqXmuJ-c',
    appId: '1:87445559755:web:dae9b62c2a9a1087873e4e',
    messagingSenderId: '87445559755',
    projectId: 'wallet-ad6ea',
    authDomain: 'wallet-ad6ea.firebaseapp.com',
    storageBucket: 'wallet-ad6ea.firebasestorage.app',
  );

  static const FirebaseOptions android =FirebaseOptions(
    apiKey: 'AIzaSyB5Yi_jmy1-1UofYUw_PTeVzuLSNHe2mm4',
    appId: '1:87445559755:android:849bbd374f7fdc3d873e4e',
    messagingSenderId: '87445559755',
    projectId: 'wallet-ad6ea',
    storageBucket: 'wallet-ad6ea.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyA_hbKcI9cv6Fgm1Xo6n4QC7TWQEzBjyNI',
    appId: '1:87445559755:ios:7edb6009b2615af5873e4e',
    messagingSenderId: '87445559755',
    projectId: 'wallet-ad6ea',
    storageBucket: 'wallet-ad6ea.firebasestorage.app',
    iosBundleId: 'com.couple.coupleLedger',
  );
}
