import 'package:couple_ledger/parser/dividend_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 10, 27, 9, 0);

  test('토스증권 달러 배당', () {
    final d = DividendParser.parse('MSTW 배당금 입금\n토스증권 계좌로 9.51달러가 입금됐어요', now: now)!;
    expect(d.name, 'MSTW');
    expect(d.broker, '토스증권');
    expect(d.amount, 9.51);
    expect(d.usd, true);
    expect(d.date, now);
  });

  test('토스증권 원화 배당', () {
    final d = DividendParser.parse('삼성전자 배당금 입금\n토스증권 계좌로 1,444원이 입금됐어요', now: now)!;
    expect(d.name, '삼성전자');
    expect(d.amount, 1444);
    expect(d.usd, false);
  });

  test('\$ 표기와 천 단위 쉼표', () {
    final d = DividendParser.parse('SCHD 배당금 입금\n토스증권 계좌로 \$1,234.50가 입금됐어요', now: now)!;
    expect(d.amount, 1234.5);
    expect(d.usd, true);
  });

  test('배당 알림이 아니면 null', () {
    expect(DividendParser.parse('9650원 결제\nKB 국민카드 | 쿠팡', now: now), isNull);
    expect(DividendParser.parse('MSTW 배당금 입금', now: now), isNull);
    expect(DividendParser.parse('MSTW 배당 예정 안내\n다음 주에 입금돼요', now: now), isNull);
  });
}
