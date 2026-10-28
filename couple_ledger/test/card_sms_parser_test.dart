import 'package:couple_ledger/parser/card_sms_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 10, 26, 20, 0);

  test('신한카드', () {
    final p = CardSmsParser.parse(
        '[Web발신]\n신한카드(1234)승인 홍길동\n12,300원(일시불)\n10/26 14:30\n스타벅스 강남점',
        now: now)!;
    expect(p.card, '신한카드');
    expect(p.amount, 12300);
    expect(p.merchant, '스타벅스 강남점');
    expect(p.date, DateTime(2026, 10, 26, 14, 30));
    expect(p.canceled, false);
  });

  test('삼성카드', () {
    final p = CardSmsParser.parse(
        '[Web발신]\n삼성 1234승인\n홍*동\n45,000원 일시불\n10/26 09:12\n이마트 성수점\n누적 1,234,000원',
        now: now)!;
    expect(p.card, '삼성카드');
    expect(p.amount, 45000);
    expect(p.merchant, '이마트 성수점');
  });

  test('삼성카드 실제 카톡 알림 형식', () {
    final p = CardSmsParser.parse(
        '삼성9453승인 백*희\n41,000원 일시불\n10/25 20:21 미소양꼬치\n누적186,550원',
        now: now)!;
    expect(p.card, '삼성카드');
    expect(p.amount, 41000);
    expect(p.merchant, '미소양꼬치');
    expect(p.date, DateTime(2026, 10, 25, 20, 21));
    expect(p.canceled, false);
  });

  test('현대카드', () {
    final p = CardSmsParser.parse(
        '현대카드 M 승인\n홍길동\n8,900원 일시불\n10/26 12:01\n맥도날드 역삼', now: now)!;
    expect(p.card, '현대카드');
    expect(p.amount, 8900);
    expect(p.merchant, '맥도날드 역삼');
  });

  test('KB국민 한 줄 형식', () {
    final p = CardSmsParser.parse(
        'KB국민카드 1234 승인 홍길동 3,500원 일시불 10/26 08:00 GS25 논현점',
        now: now)!;
    expect(p.card, 'KB국민카드');
    expect(p.amount, 3500);
    expect(p.merchant, 'GS25 논현점');
  });

  test('토스 카드 알림', () {
    final p = CardSmsParser.parse(
        '9650원 결제\nKB 국민카드 | 쿠팡(쿠페이)(일시불)', now: now)!;
    expect(p.card, 'KB국민카드');
    expect(p.amount, 9650);
    expect(p.merchant, '쿠팡(쿠페이)');
    expect(p.date, now);
    expect(p.canceled, false);
  });

  test('토스 카드 알림 할부', () {
    final p = CardSmsParser.parse(
        '120,000원 결제\n신한카드 | 하이마트(3개월)', now: now)!;
    expect(p.card, '신한카드');
    expect(p.amount, 120000);
    expect(p.merchant, '하이마트');
  });

  test('승인취소', () {
    final p = CardSmsParser.parse(
        '[Web발신]\n우리카드(1234)승인취소\n12,000원\n10/25 18:00\n쿠팡', now: now)!;
    expect(p.card, '우리카드');
    expect(p.canceled, true);
  });

  test('결제 문자가 아니면 null', () {
    expect(CardSmsParser.parse('(광고) 이벤트 안내 10,000원 쿠폰', now: now), isNull);
    expect(CardSmsParser.parse('안녕하세요', now: now), isNull);
  });

  test('여러 건 한꺼번에 (카톡 복사 형식)', () {
    const text = '''
--------------- 2026년 10월 25일 일요일 ---------------
[삼성카드] [오후 8:21] 삼성9453승인 백*희
41,000원 일시불
10/25 20:21 미소양꼬치
누적186,550원
[아내] [오후 8:30] 오늘 저녁 맛있었다 41,000원 결제했어
[삼성카드] [오전 9:05] 삼성9453승인 백*희
4,500원 일시불
10/24 09:05 스타벅스 강남점
누적145,550원
''';
    final list = CardSmsParser.parseMany(text, now: now);
    expect(list.length, 2);
    expect(list[0].merchant, '미소양꼬치');
    expect(list[1].merchant, '스타벅스 강남점');
    expect(list[1].amount, 4500);
  });

  test('빈 줄로만 구분된 여러 건', () {
    const text = '''
삼성9453승인 백*희
1,000원 일시불
10/01 10:00 A상점

삼성9453승인 백*희
2,000원 일시불
10/02 11:00 B상점
''';
    final list = CardSmsParser.parseMany(text, now: now);
    expect(list.map((e) => e.amount), [1000, 2000]);
  });

  test('롯데/농협/BC 카드', () {
    final lotte = CardSmsParser.parse(
        '[Web발신]\n롯데카드(1234)승인\n30,000원 일시불\n10/26 13:00\n교보문고',
        now: now)!;
    expect(lotte.card, '롯데카드');
    final nh = CardSmsParser.parse(
        'NH농협카드 승인 홍*동 5,000원 일시불 10/26 08:10 파리바게뜨', now: now)!;
    expect(nh.card, 'NH농협카드');
    final bc = CardSmsParser.parse(
        '[Web발신]\nBC카드 승인\n7,000원\n10/26 09:00\n김밥천국', now: now)!;
    expect(bc.card, 'BC카드');
  });

  test('가맹점 이름 속 카드사 키워드에 속지 않는다', () {
    final p = CardSmsParser.parse(
        '[Web발신]\n롯데카드(1234)승인\n52,000원 일시불\n10/26 15:00\n현대백화점 판교점',
        now: now)!;
    expect(p.card, '롯데카드');
    expect(p.merchant, '현대백화점 판교점');
    final q = CardSmsParser.parse(
        '[Web발신]\nBC카드 승인\n18,000원\n10/26 10:00\n하나로마트', now: now)!;
    expect(q.card, 'BC카드');
  });

  test('목록에 없는 카드사', () {
    final p = CardSmsParser.parse(
        '[Web발신]\n씨티카드 승인\n9,900원\n10/26 11:00\n올리브영', now: now)!;
    expect(p.card, '씨티카드');
  });

  test('롯데카드도 여러 건 가져오기에 포함된다', () {
    const text = '''
롯데카드 승인 홍*동
1,000원 일시불
10/01 10:00 A상점

삼성9453승인 백*희
2,000원 일시불
10/02 11:00 B상점
''';
    expect(CardSmsParser.parseMany(text, now: now).length, 2);
  });

  test('삼성월렛 알림', () {
    final p = CardSmsParser.parse('₩3,500 결제 완료\n(주)메가마트 스팟마트', now: now)!;
    expect(p.card, '삼성월렛');
    expect(p.amount, 3500);
    expect(p.merchant, '(주)메가마트 스팟마트');
    expect(p.date, now);
    expect(p.canceled, false);
  });

  test('삼성월렛 알림 (백슬래시 원화 기호, 카드명 포함)', () {
    final p = CardSmsParser.parse(r'\12,000 결제 완료' '\n스타벅스 강남점\n신한카드', now: now)!;
    expect(p.card, '신한카드');
    expect(p.amount, 12000);
    expect(p.merchant, '스타벅스 강남점');
  });

  test('삼성월렛 결제 취소', () {
    final p = CardSmsParser.parse('₩3,500 결제 취소\n(주)메가마트 스팟마트', now: now)!;
    expect(p.canceled, true);
    expect(p.amount, 3500);
  });
}
