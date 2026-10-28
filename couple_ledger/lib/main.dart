import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'firebase_options.dart';
import 'capture/notification_capture.dart';
import 'screens/home_screen.dart';
import 'screens/setup_screen.dart';
import 'store/ledger_store.dart';
import 'store/session.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('ko_KR');
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  final session = Session(FirebaseAuth.instance, FirebaseFirestore.instance)
    ..init();
  runApp(
    ChangeNotifierProvider.value(
      value: session,
      child: const CoupleLedgerApp(),
    ),
  );
}

class CoupleLedgerApp extends StatelessWidget {
  const CoupleLedgerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '우리 가계부',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF3B82F6),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF3B82F6),
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home: const _Root(),
    );
  }
}

/// 로그인/가계부 선택 상태에 따라 화면을 고른다.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (!s.ready) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (s.error != null) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('시작하지 못했어요.\n${s.error}', textAlign: TextAlign.center),
          ),
        ),
      );
    }
    final hid = s.householdId;
    if (hid == null) return const SetupScreen();
    return ChangeNotifierProvider(
      key: ValueKey('$hid/${s.uid}'),
      create: (_) => LedgerStore(db: s.db, householdId: hid, me: s.uid!),
      child: const HomeScreen(),
    );
  }
}

/// 카드 알림이 왔을 때 앱이 꺼져 있어도 Android가 호출하는 진입점.
/// 쌓인 알림을 파싱해 가계부(Firestore)에 바로 저장한다.
@pragma('vm:entry-point')
Future<void> backgroundSync() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
    final user = await FirebaseAuth.instance
        .authStateChanges()
        .first
        .timeout(const Duration(seconds: 10));
    if (user != null) {
      final db = FirebaseFirestore.instance;
      final doc = await db
          .collection('users')
          .doc(user.uid)
          .get()
          .timeout(const Duration(seconds: 15));
      final hid = doc.data()?['householdId'] as String?;
      // 로그인/가계부 정보가 없으면 큐를 건드리지 않고 두어 앱을 열 때 처리한다
      if (hid != null) {
        final store = LedgerStore(db: db, householdId: hid, me: user.uid);
        try {
          await store.whenLoaded().timeout(const Duration(seconds: 15));
          await NotificationCapture.sync(store);
          await store.flush().timeout(const Duration(seconds: 20));
        } finally {
          store.dispose();
        }
      }
    }
  } catch (_) {
    // 실패해도 다음 앱 실행 때 동기화되도록 조용히 종료한다
  } finally {
    await NotificationCapture.done();
  }
}
