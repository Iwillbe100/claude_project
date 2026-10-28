import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/services.dart';

import 'package:intl/intl.dart';

import '../models/transaction.dart';
import '../parser/card_sms_parser.dart';
import '../parser/dividend_parser.dart';
import '../store/ledger_store.dart';
import 'fx_rate.dart';

/// Android 알림 접근으로 쌓인 카드 결제 알림을 가계부에 반영한다.
/// iOS에서는 아무 일도 하지 않는다.
class NotificationCapture {
  static const _ch = MethodChannel('couple_ledger/capture');

  static bool get supported => !kIsWeb && Platform.isAndroid;

  static Future<bool> isEnabled() async {
    if (!supported) return false;
    return await _ch.invokeMethod<bool>('isEnabled') ?? false;
  }

  static Future<void> openSettings() async {
    if (supported) await _ch.invokeMethod('openSettings');
  }

  /// 백그라운드 엔진에게 작업이 끝났음을 알려 엔진을 종료하게 한다.
  static Future<void> done() async {
    if (supported) await _ch.invokeMethod('done');
  }

  /// 쌓인 알림을 읽어 거래로 저장하고, 새로 반영된 건수를 돌려준다.
  static Future<int> sync(LedgerStore store) async {
    if (!supported) return 0;
    final raw = await _ch.invokeListMethod<Map>('drain') ?? [];
    _rate = null;
    var added = 0;
    for (final e in raw) {
      final body = e['body'] as String;
      final time = DateTime.fromMillisecondsSinceEpoch(e['time'] as int);
      final d = DividendParser.parse(body, now: time);
      if (d != null) {
        if (await store.addIfNew(await _dividend(d, store))) added++;
        continue;
      }
      final p = CardSmsParser.parse(body, now: time);
      if (p == null) continue;
      if (p.canceled) {
        await store.cancelMatching(p.amount, p.merchant, p.date);
        continue;
      }
      final ok = await store.addIfNew(
        p.toTransaction(
          id: store.newId(),
          author: store.me,
          categoryId: store.categoryFor(p.merchant),
        ),
      );
      if (ok) added++;
    }
    return added;
  }

  static double? _rate; // 한 번 동기화하는 동안은 같은 환율을 쓴다

  /// 달러 배당은 입금 시점 환율로 원화로 바꾸고, 원래 금액과 환율을 메모에 남긴다.
  static Future<Transaction> _dividend(ParsedDividend d, LedgerStore store) async {
    var amount = d.amount.round();
    var memo = '';
    if (d.usd) {
      final rate = _rate ??= await FxRate.usdKrw();
      amount = (d.amount * rate).round();
      memo = '${d.amount}달러 · 1달러=${NumberFormat('#,###').format(rate.round())}원';
    }
    return Transaction(
      id: store.newId(),
      date: d.date,
      amount: amount,
      type: TxType.income,
      merchant: '${d.name} 배당금',
      categoryId: 'dividend',
      card: d.broker,
      author: store.me,
      auto: true,
      memo: memo,
    );
  }
}
