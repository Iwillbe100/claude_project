enum TxType { expense, income }

/// 수입 카테고리를 묶어 보는 큰 분류.
enum IncomeGroup {
  fixed('고정수입'),
  invest('투자수입'),
  other('기타수입');

  final String label;
  const IncomeGroup(this.label);
}

class Category {
  final String id;
  final String name;
  final String emoji;
  final IncomeGroup? group; // 수입 카테고리만 있다
  const Category(this.id, this.name, this.emoji, [this.group]);

  bool get isIncome => group != null;
}

const categories = <Category>[
  Category('food', '식비', '🍚'),
  Category('cafe', '카페/간식', '☕'),
  Category('transport', '교통', '🚌'),
  Category('living', '생활/마트', '🛒'),
  Category('housing', '주거/통신', '🏠'),
  Category('health', '의료', '💊'),
  Category('culture', '문화/여가', '🎬'),
  Category('shopping', '쇼핑', '🛍️'),
  Category('coupang', '쿠팡', '🚀'),
  Category('baby', '육아/교육', '🍼'),
  Category('etc', '기타', '📦'),
  Category('salary', '급여', '💰', IncomeGroup.fixed),
  Category('sale', '판매수익', '📈', IncomeGroup.invest),
  Category('dividend', '배당수익', '💵', IncomeGroup.invest),
  Category('interest', '이자수익', '🏦', IncomeGroup.invest),
  Category('bonus', '상여금', '🎉', IncomeGroup.other),
  Category('gift', '용돈/선물', '🎁', IncomeGroup.other),
  Category('income_etc', '기타수입', '💸', IncomeGroup.other),
];

final expenseCategories = categories.where((c) => !c.isIncome).toList();
final incomeCategories = categories.where((c) => c.isIncome).toList();

Category categoryOf(String id) =>
    categories.firstWhere((c) => c.id == id, orElse: () => categories.firstWhere((c) => c.id == 'etc'));

/// 지점명 등을 떼어 낸 가맹점 대표 이름. 카테고리 학습의 키로 쓴다.
///  "스타벅스 강남점" → "스타벅스", "쿠팡(쿠페이)" → "쿠팡", "(주)이마트 성수" → "이마트"
String merchantKey(String merchant) {
  final m = merchant.trim().replaceFirst(RegExp(r'^(\(주\)|㈜)\s*'), '');
  final key = m.split(RegExp(r'\s+')).first.replaceAll(RegExp(r'\(.*$'), '');
  return (key.isEmpty ? m : key).toUpperCase();
}

/// 가맹점 이름으로 카테고리를 추정한다.
String guessCategory(String merchant) {
  // 위에서부터 먼저 걸리는 규칙을 쓴다 (쿠팡이츠는 식비로 보기 위해 식비가 쿠팡보다 앞에)
  const rules = <String, List<String>>{
    'cafe': ['스타벅스', '카페', '커피', '이디야', '투썸', '메가', '컴포즈', '베이커리', '파리바게'],
    'food': ['식당', '치킨', '피자', '맥도날드', '버거', '김밥', '배달의민족', '요기요', '쿠팡이츠', '국밥', '고기'],
    'coupang': ['쿠팡', '쿠페이', 'COUPANG'],
    'transport': ['택시', '지하철', '버스', '주유', 'GS칼텍스', 'SK에너지', '코레일', '티머니', '하이패스'],
    'living': ['마트', '이마트', '홈플러스', 'GS25', 'CU', '세븐일레븐', '다이소', '올리브영'],
    'housing': ['KT', 'SKT', 'LGU', '관리비', '전기', '가스', '통신'],
    'health': ['병원', '의원', '약국', '치과'],
    'culture': ['CGV', '메가박스', '롯데시네마', '넷플릭스', '영화', '유튜브'],
    'shopping': ['11번가', '무신사', '지마켓', '옥션', '네이버페이'],
    'baby': ['학원', '어린이집', '유치원', '장난감'],
  };
  final m = merchant.toUpperCase();
  for (final e in rules.entries) {
    if (e.value.any((k) => m.contains(k.toUpperCase()))) return e.key;
  }
  return 'etc';
}

/// 수입 내용으로 카테고리를 추정한다. 아무 것도 안 걸리면 급여로 본다.
String guessIncomeCategory(String merchant) {
  const rules = <String, List<String>>{
    'dividend': ['배당'],
    'interest': ['이자'],
    'sale': ['매도', '판매', '차익', '수익'],
    'bonus': ['상여', '성과급', '보너스', '인센티브'],
    'gift': ['용돈', '선물', '축의', '세뱃돈'],
    'income_etc': ['환급', '환불', '캐시백'],
  };
  final m = merchant.toUpperCase();
  for (final e in rules.entries) {
    if (e.value.any((k) => m.contains(k))) return e.key;
  }
  return 'salary';
}

class Transaction {
  final String id;
  final DateTime date;
  final int amount; // 원, 항상 양수
  final TxType type;
  final String merchant;
  final String categoryId;
  final String card; // 카드사/카드명, 수동 입력이면 빈 문자열
  final String author; // 입력한 사람 (me / spouse 등)
  final String owner; // 쓴 사람 uid (용돈에서 차감), 공용이면 빈 문자열
  final bool auto; // 자동 입력 여부
  final String memo;

  const Transaction({
    required this.id,
    required this.date,
    required this.amount,
    required this.type,
    required this.merchant,
    required this.categoryId,
    this.card = '',
    this.author = '',
    this.owner = '',
    this.auto = false,
    this.memo = '',
  });

  /// 제3자(어머님 등)가 쓴 기타비용. 생활비 예산과 용돈 어디에도 포함하지 않는다.
  static const thirdParty = '_other';

  bool get shared => owner.isEmpty;
  bool get excluded => owner == thirdParty;

  Transaction copyWith({
    DateTime? date,
    int? amount,
    TxType? type,
    String? merchant,
    String? categoryId,
    String? card,
    String? owner,
    String? memo,
  }) =>
      Transaction(
        id: id,
        date: date ?? this.date,
        amount: amount ?? this.amount,
        type: type ?? this.type,
        merchant: merchant ?? this.merchant,
        categoryId: categoryId ?? this.categoryId,
        card: card ?? this.card,
        author: author,
        owner: owner ?? this.owner,
        auto: auto,
        memo: memo ?? this.memo,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'date': date.toIso8601String(),
        'amount': amount,
        'type': type.name,
        'merchant': merchant,
        'categoryId': categoryId,
        'card': card,
        'author': author,
        'owner': owner,
        'auto': auto,
        'memo': memo,
      };

  factory Transaction.fromJson(Map<String, dynamic> j) => Transaction(
        id: j['id'] as String,
        date: DateTime.parse(j['date'] as String),
        amount: j['amount'] as int,
        type: TxType.values.byName(j['type'] as String),
        merchant: j['merchant'] as String,
        categoryId: j['categoryId'] as String,
        card: (j['card'] ?? '') as String,
        author: (j['author'] ?? '') as String,
        owner: (j['owner'] ?? '') as String,
        auto: (j['auto'] ?? false) as bool,
        memo: (j['memo'] ?? '') as String,
      );
}
