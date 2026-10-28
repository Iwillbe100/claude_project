import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// 로그인(익명)과 "어느 가계부에 속하는가"를 관리한다.
class Session extends ChangeNotifier {
  final FirebaseAuth auth;
  final FirebaseFirestore db;

  String? uid;
  String? householdId;
  bool ready = false;
  String? error;

  Session(this.auth, this.db);

  bool get isAnonymous => auth.currentUser?.isAnonymous ?? true;
  String? get email => auth.currentUser?.email;


  // Firebase가 만들어 준 웹 클라이언트 ID (Android 구글 로그인 토큰 발급용)
  static const _webClientId =
      '87445559755-erpmq8a18tog63d03ds4hu2q9j2kqcr7.apps.googleusercontent.com';

  // 헷갈리는 문자(0/O, 1/I)는 뺀 초대 코드 문자
  static const _alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

  Future<void> init() async {
    try {
      var user = auth.currentUser;
      user ??= (await auth.signInAnonymously()).user;
      uid = user!.uid;
      final doc = await db.collection('users').doc(uid).get();
      householdId = doc.data()?['householdId'] as String?;
    } catch (e) {
      error = '$e';
    }
    ready = true;
    notifyListeners();
  }

  /// 구글 계정을 연결하거나, 이미 가계부가 있는 구글 계정이면 그 계정으로 전환한다.
  /// 처음 연결할 때는 익명 계정을 그대로 승격하므로 기존 데이터가 유지된다.
  /// 성공하면 null, 실패하면 사용자에게 보여줄 메시지를 돌려준다.
  Future<String?> connectGoogle() async {
    try {
      final user = auth.currentUser;
      final anonymous = user != null && user.isAnonymous;
      try {
        if (kIsWeb) {
          final provider = GoogleAuthProvider();
          if (anonymous) {
            await user.linkWithPopup(provider);
          } else {
            await auth.signInWithPopup(provider);
          }
        } else {
          // 앱 안에서 기기의 구글 계정을 직접 고르는 방식 (브라우저 리다이렉트 없음)
          final account = await GoogleSignIn(serverClientId: _webClientId).signIn();
          if (account == null) return null; // 사용자가 취소
          final tokens = await account.authentication;
          final credential = GoogleAuthProvider.credential(
            accessToken: tokens.accessToken,
            idToken: tokens.idToken,
          );
          if (anonymous) {
            await user.linkWithCredential(credential);
          } else {
            await auth.signInWithCredential(credential);
          }
        }
      } on FirebaseAuthException catch (e) {
        // 이미 다른 곳에서 쓰던 구글 계정이면 그 계정으로 로그인한다
        if (e.code == 'credential-already-in-use' && e.credential != null) {
          await auth.signInWithCredential(e.credential!);
        } else {
          rethrow;
        }
      }
      await _reload();
      return null;
    } on FirebaseAuthException catch (e) {
      if (e.code == 'popup-closed-by-user' ||
          e.code == 'cancelled-popup-request') {
        return null;
      }
      return '구글 로그인에 실패했어요 (${e.code})';
    } catch (e) {
      return '구글 로그인에 실패했어요: $e';
    }
  }

  Future<void> _reload() async {
    uid = auth.currentUser!.uid;
    final doc = await db.collection('users').doc(uid).get();
    householdId = doc.data()?['householdId'] as String?;
    notifyListeners();
  }

  Future<void> createHousehold() async {
    final rnd = Random.secure();
    final code =
        List.generate(8, (_) => _alphabet[rnd.nextInt(_alphabet.length)]).join();
    await db.collection('households').doc(code).set({
      'members': [uid],
      'budget': 2000000,
      'createdAt': FieldValue.serverTimestamp(),
    });
    await _attach(code);
  }

  /// 성공하면 null, 실패하면 사용자에게 보여줄 메시지를 돌려준다.
  Future<String?> joinHousehold(String rawCode) async {
    final code = rawCode.trim().toUpperCase();
    if (code.length != 8) return '초대 코드는 8자리예요';
    final ref = db.collection('households').doc(code);
    final snap = await ref.get();
    if (!snap.exists) return '없는 초대 코드예요';
    final members = List<String>.from(snap.data()!['members'] as List);
    if (!members.contains(uid)) {
      if (members.length >= 2) return '이미 두 명이 쓰고 있는 가계부예요';
      await ref.update({'members': FieldValue.arrayUnion([uid])});
    }
    await _attach(code);
    return null;
  }

  /// 가계부에서 나간다. 구성원 목록에서도 빠져야 자리가 비어 다시(또는 다른 계정으로) 참여할 수 있다.
  Future<void> leave() async {
    final hid = householdId;
    if (hid != null) {
      // 구성원일 때만 수정 권한이 있으므로 users 문서보다 먼저 처리한다
      await db.collection('households').doc(hid).update({
        'members': FieldValue.arrayRemove([uid]),
      });
    }
    await db.collection('users').doc(uid).delete();
    householdId = null;
    notifyListeners();
  }

  Future<void> _attach(String code) async {
    await db.collection('users').doc(uid).set({'householdId': code});
    householdId = code;
    notifyListeners();
  }
}
