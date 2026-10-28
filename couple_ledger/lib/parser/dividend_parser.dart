/// 증권사 배당금 입금 알림 한 건을 파싱한 결과.
class ParsedDividend {
  final String name; // 종목 ("MSTW", "삼성전자")
  final String broker; // "토스증권"
  final double amount; // usd면 달러, 아니면 원
  final bool usd;
  final DateTime date;

  const ParsedDividend({
    required this.name,
    required this.broker,
    required this.amount,
    required this.usd,
    required this.date,
  });
}

/// 토스증권 배당 알림을 해석한다.
///  "MSTW 배당금 입금\n토스증권 계좌로 9.51달러가 입금됐어요"
///  "삼성전자 배당금 입금\n토스증권 계좌로 1,234원이 입금됐어요"
class DividendParser {
  static final _titleRe = RegExp(r'^(.+?)\s*배당금\s*입금');
  static final _usdRe = RegExp(r'(?:\$\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*달러)');
  static final _krwRe = RegExp(r'([\d,]+)\s*원');
  static final _brokerRe = RegExp(r'([가-힣A-Za-z]+증권)');

  /// 배당 알림이 아니면 null.
  static ParsedDividend? parse(String text, {DateTime? now}) {
    final lines = text
        .replaceAll('\r', '')
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    if (lines.length < 2) return null;
    final title = _titleRe.firstMatch(lines.first);
    if (title == null) return null;
    final rest = lines.skip(1).join(' ');

    final double amount;
    final bool usd;
    final u = _usdRe.firstMatch(rest);
    final k = _krwRe.firstMatch(rest);
    if (u != null) {
      amount = double.parse((u.group(1) ?? u.group(2))!.replaceAll(',', ''));
      usd = true;
    } else if (k != null) {
      amount = double.parse(k.group(1)!.replaceAll(',', ''));
      usd = false;
    } else {
      return null;
    }
    if (amount <= 0) return null;

    return ParsedDividend(
      name: title.group(1)!.trim(),
      broker: _brokerRe.firstMatch(rest)?.group(1) ?? '',
      amount: amount,
      usd: usd,
      date: now ?? DateTime.now(),
    );
  }
}
