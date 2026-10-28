import 'transaction.dart';

/// 매달 같은 날 자동으로 들어가는 고정지출/고정수입 (월세, 통신비, 구독, 급여 등).
class Recurring {
  final String id;
  final String merchant;
  final int amount;
  final TxType type;
  final String categoryId;
  final String owner; // Transaction.owner와 같은 의미
  final int day; // 1~31, 그 달에 없는 날이면 말일
  final String done; // 마지막으로 만든 달 "yyyyMM"

  const Recurring({
    required this.id,
    required this.merchant,
    required this.amount,
    required this.type,
    required this.categoryId,
    this.owner = '',
    required this.day,
    required this.done,
  });

  static String monthKey(DateTime m) =>
      '${m.year}${m.month.toString().padLeft(2, '0')}';

  static DateTime parseMonth(String k) =>
      DateTime(int.parse(k.substring(0, 4)), int.parse(k.substring(4)));

  /// 그 달의 실제 결제일 (31일 설정이면 2월은 28/29일).
  DateTime dateIn(DateTime month) {
    final last = DateTime(month.year, month.month + 1, 0).day;
    return DateTime(month.year, month.month, day > last ? last : day, 9);
  }

  /// 생성되는 거래의 id. 두 사람 기기에서 동시에 만들어도 한 건만 남는다.
  String txId(DateTime month) => 'rec_${id}_${monthKey(month)}';

  Recurring copyWith({String? done}) => Recurring(
        id: id,
        merchant: merchant,
        amount: amount,
        type: type,
        categoryId: categoryId,
        owner: owner,
        day: day,
        done: done ?? this.done,
      );

  Map<String, dynamic> toJson() => {
        'merchant': merchant,
        'amount': amount,
        'type': type.name,
        'categoryId': categoryId,
        'owner': owner,
        'day': day,
        'done': done,
      };

  factory Recurring.fromJson(String id, Map<String, dynamic> j) => Recurring(
        id: id,
        merchant: j['merchant'] as String,
        amount: (j['amount'] as num).toInt(),
        type: TxType.values.byName(j['type'] as String),
        categoryId: j['categoryId'] as String,
        owner: (j['owner'] ?? '') as String,
        day: (j['day'] as num).toInt(),
        done: j['done'] as String,
      );
}
