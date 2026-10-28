import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const FamilyGamesApp());
}

class FamilyGamesApp extends StatelessWidget {
  const FamilyGamesApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '가족 게임판',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(scaffoldBackgroundColor: const Color(0xFFEAF2F4)),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D1C22),
      ),
      home: const GameScreen(),
    );
  }
}

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent)
      // The page calls Haptic.postMessage(...) where a browser would vibrate.
      ..addJavaScriptChannel('Haptic', onMessageReceived: (_) {
        HapticFeedback.heavyImpact();
      })
      ..loadFlutterAsset('assets/www/game.html');
  }

  Future<void> _onBack() async {
    try {
      final handled = await _controller.runJavaScriptReturningResult('appBack()');
      if (handled == true || handled.toString() == 'true') return;
    } catch (_) {}
    SystemNavigator.pop();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _onBack();
      },
      child: Scaffold(
        body: SafeArea(child: WebViewWidget(controller: _controller)),
      ),
    );
  }
}
