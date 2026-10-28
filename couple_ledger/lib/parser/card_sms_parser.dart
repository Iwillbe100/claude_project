import '../models/transaction.dart';

/// 카드 결제 문자/알림 한 건을 파싱한 결과.
class ParsedPayment {
  final String card;
  final int amount;
  final String merchant;
  final DateTime date;
  final bool canceled;

  const ParsedPayment({
    required this.card,
    required this.amount,
    required this.merchant,
    required this.date,
    this.canceled = false,
  });

  Transaction toTransaction({
    required String id,
    required String author,
    String? categoryId,
  }) =>
      Transaction(
        id: id,
        date: date,
        amount: amount,
        type: TxType.expense,
        merchant: merchant,
        categoryId: categoryId ?? guessCategory(merchant),
        card: card,
        author: author,
        auto: true,
      );
}

/// 카드사 결제 문자를 해석한다. 카드사별 형식이 달라서 공통 규칙으로 처리한다.
///  - 카드사: 본문 앞부분의 카드사 키워드
///  - 금액: "12,300원"
///  - 일시: "10/26 14:30" 형태 (없으면 [now])
///  - 가맹점: 일시 뒤 또는 금액 뒤의 텍스트
class CardSmsParser {
  static const _issuers = <String, String>{
    '삼성': '삼성카드',
    '현대': '현대카드',
    '신한': '신한카드',
    'KB': 'KB국민카드',
    '국민': 'KB국민카드',
    '우리': '우리카드',
    '하나': '하나카드',
    '롯데': '롯데카드',
    'NH': 'NH농협카드',
    '농협': 'NH농협카드',
    'BC': 'BC카드',
    '비씨': 'BC카드',
  };

  // 목록에 없는 카드사 ("씨티카드" 등)
  static final _otherCardRe = RegExp(r'([가-힣A-Za-z]{2,6})카드');

  static final _amountRe = RegExp(r'([\d,]+)\s*원');
  // 삼성월렛 알림 제목: "₩3,500 결제 완료" (\는 한글 글꼴에서 ₩로 보이는 문자)
  static final _walletRe = RegExp(r'^[₩\\]\s*([\d,]+)\s*(결제|승인)');
  static final _dateRe = RegExp(r'(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})');
  static final _installRe = RegExp(r'\(?\s*(일시불|\d+개월)\s*\)?');
  static final _cardNoRe = RegExp(r'\d{4}\*+|\(\d{4}\)');

  // 카톡 내보내기/복사 시 메시지마다 붙는 머리말
  //  "[삼성카드] [오후 8:21] ..." 또는 "2025. 10. 25. 오후 8:21, 삼성카드 : ..."
  static final _headerRe = RegExp(
    r'^(\[[^\]]+\]\s*\[(오전|오후)\s*\d{1,2}:\d{2}\]\s*'
    r'|\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(오전|오후)\s*\d{1,2}:\d{2},\s*[^:]+:\s*)',
  );

  /// 여러 건이 섞인 텍스트(카톡 대화 복사/내보내기)에서 결제 문자를 모두 찾는다.
  /// 결제가 아닌 대화는 건너뛴다. 머리말이 없으면 빈 줄 기준으로 나눈다.
  static List<ParsedPayment> parseMany(String text, {DateTime? now}) {
    now ??= DateTime.now();
    final lines = text.replaceAll('\r', '').split('\n');
    final chunks = <String>[];
    var cur = StringBuffer();
    var sawHeader = false;

    void flush() {
      final s = cur.toString().trim();
      if (s.isNotEmpty) chunks.add(s);
      cur = StringBuffer();
    }

    for (final raw in lines) {
      final line = raw.trimRight();
      final h = _headerRe.firstMatch(line);
      if (h != null) {
        sawHeader = true;
        flush();
        cur.writeln(line.substring(h.end));
      } else if (!sawHeader && line.trim().isEmpty) {
        flush();
      } else {
        cur.writeln(line);
      }
    }
    flush();

    return [
      for (final c in chunks)
        // 대화 속 "얼마 결제했어" 같은 말이 섞이지 않게 카드사가 확인된 것만 인정
        if (parse(c, now: now) case final p? when p.card.isNotEmpty) p,
    ];
  }

  /// 결제 문자가 아니면 null.
  static ParsedPayment? parse(String text, {DateTime? now}) {
    now ??= DateTime.now();
    final body = text.replaceAll('\r', '').trim();
    if (body.isEmpty) return null;

    final wallet = _parseWallet(body, now);
    if (wallet != null) return wallet;

    final amountMatch = _amountRe.firstMatch(body);
    if (amountMatch == null) return null;

    final isPayment = body.contains('승인') ||
        body.contains('결제') ||
        body.contains('사용');
    if (!isPayment) return null;
    // 광고/안내 문자 제외
    if (body.contains('(광고)') || body.contains('한도') && !body.contains('승인')) {
      return null;
    }

    final canceled = body.contains('취소');
    final amount = int.parse(amountMatch.group(1)!.replaceAll(',', ''));
    if (amount <= 0) return null;


    var date = now;
    final dm = _dateRe.firstMatch(body);
    if (dm != null) {
      final month = int.parse(dm.group(1)!);
      final day = int.parse(dm.group(2)!);
      var year = now.year;
      var d = DateTime(year, month, day, int.parse(dm.group(3)!), int.parse(dm.group(4)!));
      // 연말에 1월 문자가 오는 등 미래 날짜가 되면 작년으로 본다
      if (d.isAfter(now.add(const Duration(days: 1)))) {
        d = DateTime(year - 1, month, day, d.hour, d.minute);
      }
      date = d;
    }

    final merchant = _extractMerchant(body, amountMatch, dm);
    if (merchant.isEmpty) return null;

    final card = _detectCard(body, merchant);

    return ParsedPayment(
      card: card,
      amount: amount,
      merchant: merchant,
      date: date,
      canceled: canceled,
    );
  }

  /// 삼성월렛 알림: 첫 줄 "₩3,500 결제 완료", 다음 줄 가맹점.
  /// 일시가 없어서 알림 시각을 쓰고, 카드사가 안 보이면 '삼성월렛'으로 둔다.
  static ParsedPayment? _parseWallet(String body, DateTime now) {
    final lines = body
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    if (lines.length < 2) return null;
    final m = _walletRe.firstMatch(lines.first);
    if (m == null) return null;
    final amount = int.parse(m.group(1)!.replaceAll(',', ''));
    if (amount <= 0) return null;
    final merchant = _clean(lines[1]);
    if (merchant.isEmpty) return null;
    final card = _detectCard(lines.skip(2).join('\n'), merchant);
    return ParsedPayment(
      card: card.isEmpty ? '삼성월렛' : card,
      amount: amount,
      merchant: merchant,
      date: now,
      canceled: lines.first.contains('취소'),
    );
  }

  /// 가맹점 이름("하나로마트", "현대백화점")에 걸리지 않도록 가맹점을 뺀 본문에서,
  /// 가장 앞에 나오는 카드사를 고른다.
  static String _detectCard(String body, String merchant) {
    final rest = body.replaceFirst(merchant, ' ');
    String card = '';
    var best = -1;
    for (final e in _issuers.entries) {
      final i = rest.indexOf(e.key);
      if (i >= 0 && (best < 0 || i < best)) {
        best = i;
        card = e.value;
      }
    }
    if (card.isEmpty && rest.contains('승인')) {
      final m = _otherCardRe.firstMatch(rest);
      if (m != null) card = '${m.group(1)}카드';
    }
    return card;
  }

  static String _extractMerchant(String body, RegExpMatch amount, RegExpMatch? dm) {
    final lines = body
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();

    bool isNoise(String l) =>
        _amountRe.hasMatch(l) ||
        _dateRe.hasMatch(l) && l.replaceAll(_dateRe, '').trim().isEmpty ||
        l.startsWith('[') ||
        l.startsWith('누적') ||
        l.contains('잔액') ||
        l.contains('한도') ||
        l.contains('승인') && l.length < 12 ||
        l.contains('Web발신');

    // 1) 일시 뒤에 같은 줄로 이어진 가맹점 ("10/26 14:30 스타벅스 강남점")
    if (dm != null) {
      final after = body.substring(dm.end);
      final firstLine = after.split('\n').first.trim();
      final cleaned = _clean(firstLine);
      if (cleaned.isNotEmpty && !_amountRe.hasMatch(cleaned)) return cleaned;
    }

    // 2) 토스 알림: "KB 국민카드 | 쿠팡(쿠페이)(일시불)" 처럼 | 뒤가 가맹점
    for (final l in lines) {
      final bar = l.lastIndexOf('|');
      if (bar < 0) continue;
      final c = _clean(l.substring(bar + 1));
      if (c.isNotEmpty && !_amountRe.hasMatch(c)) return c;
    }

    // 3) 금액 같은 줄에서 금액 뒤 텍스트 ("12,300원 일시불 스타벅스")
    final amountLine = lines.firstWhere(
      (l) => _amountRe.hasMatch(l),
      orElse: () => '',
    );
    final am = _amountRe.firstMatch(amountLine);
    if (am != null) {
      final tail = _clean(amountLine.substring(am.end));
      if (tail.isNotEmpty) return tail;
    }

    // 4) 노이즈가 아닌 마지막 줄
    for (final l in lines.reversed) {
      if (isNoise(l)) continue;
      final c = _clean(l);
      if (c.isNotEmpty) return c;
    }
    return '';
  }

  static String _clean(String s) => s
      .replaceAll(_installRe, ' ')
      .replaceAll(_cardNoRe, ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .replaceAll(RegExp(r'^[\s\-:]+|[\s\-:]+$'), '')
      .trim();
}
