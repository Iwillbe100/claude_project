import 'dart:convert';
import 'dart:io';

import 'package:shared_preferences/shared_preferences.dart';

/// 달러 배당을 원화로 기록할 때 쓰는 환율. 받아 오지 못하면 마지막으로 받은 값을 쓴다.
class FxRate {
  static const _key = 'usdKrw';
  static const _fallback = 1400.0;
  static const _url = 'https://open.er-api.com/v6/latest/USD';

  static Future<double> usdKrw() async {
    final prefs = await SharedPreferences.getInstance();
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    try {
      final res = await (await client.getUrl(Uri.parse(_url)))
          .close()
          .timeout(const Duration(seconds: 8));
      final j = jsonDecode(await res.transform(utf8.decoder).join()) as Map;
      final rate = ((j['rates'] as Map)['KRW'] as num).toDouble();
      await prefs.setDouble(_key, rate);
      return rate;
    } catch (_) {
      return prefs.getDouble(_key) ?? _fallback;
    } finally {
      client.close();
    }
  }
}
