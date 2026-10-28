import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart' hide Transaction;
import 'package:flutter/foundation.dart';

import '../models/recurring.dart';
import '../models/transaction.dart';

/// 부부가 공유하는 가계부. Firestore의 households/{householdId} 아래에 저장되며
/// 실시간으로 동기화된다. 오프라인에서도 쓸 수 있고 연결되면 자동 반영된다.
class LedgerStore extends ChangeNotifier {
  final String householdId;
  final String me;
  final FirebaseFirestore _db;
  final Completer<void> _loaded = Completer<void>();
  final Completer<void> _hhLoaded = Completer<void>();
  final DocumentReference<Map<String, dynamic>> _hh;
  late final CollectionReference<Map<String, dynamic>> _tx;
  final List<StreamSubscription> _subs = [];

  static const defaultAllowance = 300000;

  List<Transaction> _items = [];
  int monthlyBudget = 2000000;
  List<String> members = [];
  Map<String, int> _allowances = {};
  // 이미 반영한 승인취소 기록 (금액, 취소 시각). 같은 취소가 카톡/문자로 두 번 와도 한 번만 지운다.
  List<({int amount, DateTime at})> _cancels = [];
  // 가맹점 대표 이름(merchantKey) → 사용자가 고른 카테고리. 두 사람이 함께 쓴다.
  Map<String, String> _rules = {};
  List<Recurring> recurring = [];
  // 카테고리 id → 월 예산. 정하지 않은 카테고리는 없음.
  Map<String, int> categoryBudgets = {};
  bool loaded = false;

  int get memberCount => members.isEmpty ? 1 : members.length;

  /// 배우자 uid. 아직 참여하지 않았으면 null.
  String? get spouse {
    for (final m in members) {
      if (m != me) return m;
    }
    return null;
  }

  LedgerStore({
    required FirebaseFirestore db,
    required this.householdId,
    required this.me,
  })  : _db = db,
        _hh = db.collection('households').doc(householdId) {
    _tx = _hh.collection('transactions');
    _subs.add(_tx.snapshots().listen((snap) {
      _items = snap.docs.map((d) => Transaction.fromJson(d.data())).toList();
      loaded = true;
      if (!_loaded.isCompleted) _loaded.complete();
      _autoRecurring();
      notifyListeners();
    }));
    _subs.add(_hh.snapshots().listen((snap) {
      if (!_hhLoaded.isCompleted) _hhLoaded.complete();
      final d = snap.data();
      if (d == null) return;
      monthlyBudget = (d['budget'] as num?)?.toInt() ?? monthlyBudget;
      members = List<String>.from((d['members'] as List?) ?? const []);
      _allowances = ((d['allowances'] as Map?) ?? const {})
          .map((k, v) => MapEntry(k as String, (v as num).toInt()));
      _cancels = [
        for (final c in (d['cancels'] as List?) ?? const [])
          (
            amount: ((c as Map)['amount'] as num).toInt(),
            at: DateTime.fromMillisecondsSinceEpoch((c['at'] as num).toInt()),
          ),
      ];
      categoryBudgets = ((d['categoryBudgets'] as Map?) ?? const {})
          .map((k, v) => MapEntry(k as String, (v as num).toInt()));
      _rules = ((d['categoryRules'] as Map?) ?? const {})
          .map((k, v) => MapEntry(k as String, v as String));
      recurring = [
        for (final e in ((d['recurring'] as Map?) ?? const {}).entries)
          Recurring.fromJson(
              e.key as String, Map<String, dynamic>.from(e.value as Map)),
      ]..sort((a, b) => a.day.compareTo(b.day));
      _autoRecurring();
      notifyListeners();
    }));
  }

  /// 첫 스냅샷(캐시 포함)이 올 때까지 기다린다. 중복 검사 전에 호출한다.
  Future<void> whenLoaded() => Future.wait([_loaded.future, _hhLoaded.future]);

  /// 서버에 아직 못 간 쓰기가 끝날 때까지 기다린다. 백그라운드 동기화 마무리용.
  Future<void> flush() => _db.waitForPendingWrites();

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    super.dispose();
  }

  List<Transaction> get all => List.unmodifiable(_items);

  List<Transaction> inMonth(DateTime month) {
    final list = _items
        .where((t) => t.date.year == month.year && t.date.month == month.month)
        .toList()
      ..sort((a, b) => b.date.compareTo(a.date));
    return list;
  }

  /// 기타비용(제3자)은 우리 생활비가 아니므로 합계에서 뺀다.
  int total(DateTime month, TxType type) => inMonth(month)
      .where((t) => t.type == type && !t.excluded)
      .fold(0, (s, t) => s + t.amount);

  String ownerLabel(String owner) => owner.isEmpty
      ? '공용'
      : owner == Transaction.thirdParty
          ? '기타비용'
          : (owner == me ? '나' : '배우자');

  int allowanceOf(String uid) => _allowances[uid] ?? defaultAllowance;

  /// 해당 달에 owner가 쓴 지출 합계. owner가 빈 문자열이면 공용 지출.
  int spentBy(DateTime month, String owner) => inMonth(month)
      .where((t) => t.type == TxType.expense && t.owner == owner)
      .fold(0, (s, t) => s + t.amount);

  /// [end]까지 최근 [n]개월의 지출 합계 (오래된 달부터).
  List<int> monthlyExpense(DateTime end, int n) => [
        for (var i = n - 1; i >= 0; i--)
          total(DateTime(end.year, end.month - i), TxType.expense),
      ];

  Map<String, int> expenseByCategory(DateTime month) =>
      _byCategory(month, TxType.expense);

  Map<String, int> incomeByCategory(DateTime month) =>
      _byCategory(month, TxType.income);

  Map<String, int> _byCategory(DateTime month, TxType type) {
    final m = <String, int>{};
    for (final t in inMonth(month).where((t) => t.type == type && !t.excluded)) {
      m[t.categoryId] = (m[t.categoryId] ?? 0) + t.amount;
    }
    return m;
  }

  // 쓰기는 기다리지 않는다. 오프라인이면 서버 응답이 올 때까지 Future가 끝나지 않지만,
  // 로컬 스냅샷은 즉시 갱신되므로 화면에는 바로 반영된다.
  Future<void> add(Transaction t) {
    unawaited(_tx.doc(t.id).set(t.toJson()));
    return Future.value();
  }

  /// 자동 입력용. 같은 카드/금액/가맹점이 1분 안에 이미 있으면 중복으로 보고 건너뛴다.
  Future<bool> addIfNew(Transaction t) async {
    final dup = _items.any((o) =>
        o.amount == t.amount &&
        o.merchant == t.merchant &&
        o.type == t.type &&
        o.date.difference(t.date).abs() < const Duration(minutes: 1) ||
        _sameWalletPayment(o, t));
    if (dup) return false;
    await add(t);
    return true;
  }

  /// 삼성월렛 알림과 카드사 문자가 같은 결제로 함께 오면 가맹점 표기가 달라
  /// ("(주)메가마트 스팟마트" / "메가마트스팟마트") 금액과 시각만으로 본다.
  static bool _sameWalletPayment(Transaction o, Transaction t) =>
      (o.card == '삼성월렛' || t.card == '삼성월렛') &&
      o.auto &&
      o.type == t.type &&
      o.amount == t.amount &&
      o.date.difference(t.date).abs() < const Duration(minutes: 3);

  static const _cancelDupWindow = Duration(minutes: 3);
  static const _cancelLookback = Duration(days: 60);

  /// 승인취소 알림: 취소 시각 이전 60일 안에서 같은 금액/가맹점의 가장 최근 지출 1건을 지운다.
  /// 같은 금액의 취소가 3분 안에 또 오면(카톡+문자 중복) 이미 처리한 것으로 보고 무시한다.
  Future<void> cancelMatching(int amount, String merchant, DateTime at) async {
    final dup = _cancels.any((c) =>
        c.amount == amount && c.at.difference(at).abs() < _cancelDupWindow);
    if (dup) return;

    final matches = _items
        .where((o) =>
            o.type == TxType.expense &&
            o.amount == amount &&
            o.merchant == merchant &&
            !o.date.isAfter(at.add(const Duration(minutes: 1))) &&
            o.date.isAfter(at.subtract(_cancelLookback)))
        .toList()
      ..sort((a, b) => b.date.compareTo(a.date));
    if (matches.isEmpty) return;

    // 오래된 기록은 정리해서 문서가 계속 커지지 않게 한다
    final cutoff = DateTime.now().subtract(_cancelLookback);
    _cancels = [
      ..._cancels.where((c) => c.at.isAfter(cutoff)),
      (amount: amount, at: at),
    ];
    unawaited(_hh.update({
      'cancels': [
        for (final c in _cancels)
          {'amount': c.amount, 'at': c.at.millisecondsSinceEpoch},
      ],
    }));
    await remove(matches.first.id);
  }

  Future<void> update(Transaction t) {
    unawaited(_tx.doc(t.id).set(t.toJson()));
    return Future.value();
  }

  Future<void> remove(String id) {
    unawaited(_tx.doc(id).delete());
    return Future.value();
  }

  Future<void> setBudget(int v) {
    unawaited(_hh.update({'budget': v}));
    return Future.value();
  }

  /// 0 이하이면 그 카테고리 예산을 없앤다.
  Future<void> setCategoryBudget(String categoryId, int v) {
    unawaited(_hh.update({
      FieldPath(['categoryBudgets', categoryId]): v > 0 ? v : FieldValue.delete(),
    }));
    return Future.value();
  }

  /// 기간([from] 이상, [to] 미만)과 검색어로 내역을 찾는다. 최신순.
  /// 검색어는 가맹점, 메모, 카드, 카테고리 이름, 쓴 사람에서 찾는다.
  List<Transaction> search({
    String query = '',
    DateTime? from,
    DateTime? to,
    String? categoryId,
  }) {
    final words = query.trim().toUpperCase().split(RegExp(r'\s+'))
      ..removeWhere((w) => w.isEmpty);
    return _items.where((t) {
      if (from != null && t.date.isBefore(from)) return false;
      if (to != null && !t.date.isBefore(to)) return false;
      if (categoryId != null && t.categoryId != categoryId) return false;
      if (words.isEmpty) return true;
      final hay = [
        t.merchant,
        t.memo,
        t.card,
        categoryOf(t.categoryId).name,
        if (t.type == TxType.expense) ownerLabel(t.owner),
      ].join(' ').toUpperCase();
      return words.every(hay.contains);
    }).toList()
      ..sort((a, b) => b.date.compareTo(a.date));
  }

  Future<void> setAllowance(String uid, int v) {
    unawaited(_hh.update({'allowances.$uid': v}));
    return Future.value();
  }

  String newId() => _tx.doc().id;

  /// 예전에 고른 카테고리가 있으면 그것을, 없으면 키워드로 추정한다.
  /// 배운 카테고리가 다른 종류(지출↔수입)면 쓰지 않는다.
  String categoryFor(String merchant, {TxType type = TxType.expense}) {
    final income = type == TxType.income;
    final learned = _rules[merchantKey(merchant)];
    if (learned != null &&
        categories.any((c) => c.id == learned && c.isIncome == income)) {
      return learned;
    }
    return income ? guessIncomeCategory(merchant) : guessCategory(merchant);
  }

  /// 사용자가 카테고리를 직접 고르면 그 가맹점은 다음부터 같은 카테고리로 분류한다.
  Future<void> learnCategory(String merchant, String categoryId) {
    final key = merchantKey(merchant);
    final type = categoryOf(categoryId).isIncome ? TxType.income : TxType.expense;
    if (key.isEmpty || categoryFor(merchant, type: type) == categoryId) {
      return Future.value();
    }
    _rules[key] = categoryId;
    unawaited(_hh.update({FieldPath(['categoryRules', key]): categoryId}));
    return Future.value();
  }

  bool _sameKind(Transaction t, String key, String from) =>
      t.categoryId == from &&
      merchantKey(t.merchant) == key;

  /// 같은 가맹점에서 아직 [from] 카테고리로 남아 있는 내역 건수.
  int sameMerchant(String merchant, String from, {String? except}) {
    final key = merchantKey(merchant);
    return _items.where((t) => t.id != except && _sameKind(t, key, from)).length;
  }

  Future<void> recategorize(String merchant, String from, String to) async {
    final key = merchantKey(merchant);
    final batch = _db.batch();
    for (final t in _items.where((t) => _sameKind(t, key, from))) {
      batch.update(_tx.doc(t.id), {'categoryId': to});
    }
    unawaited(batch.commit());
  }

  Future<void> saveRecurring(Recurring r) {
    unawaited(_hh.update({FieldPath(['recurring', r.id]): r.toJson()}));
    return Future.value();
  }

  Future<void> removeRecurring(String id) {
    unawaited(_hh.update({FieldPath(['recurring', id]): FieldValue.delete()}));
    return Future.value();
  }

  // 내역과 고정지출 목록을 둘 다 받은 뒤에만 돌린다. 내역을 모르는 채로 만들면
  // 배우자가 고쳐 둔 건을 덮어쓸 수 있다.
  void _autoRecurring() {
    if (_loaded.isCompleted && _hhLoaded.isCompleted) applyRecurring();
  }

  /// 결제일이 지난 고정지출을 이번 달까지 만들어 넣고, 새로 만든 건수를 돌려준다.
  /// 만든 달은 done에 기록하므로 사용자가 지운 건은 다시 생기지 않는다.
  int applyRecurring([DateTime? now]) {
    now ??= DateTime.now();
    final current = DateTime(now.year, now.month);
    var made = 0;
    for (final r in recurring) {
      var done = r.done;
      var m = Recurring.parseMonth(done);
      while (true) {
        m = DateTime(m.year, m.month + 1);
        if (m.isAfter(current) || r.dateIn(m).isAfter(now)) break;
        final id = r.txId(m);
        // 배우자 기기가 먼저 만들었으면(수정했을 수도 있으니) 덮어쓰지 않는다
        if (!_items.any((t) => t.id == id)) {
          unawaited(_tx.doc(id).set(Transaction(
            id: id,
            date: r.dateIn(m),
            amount: r.amount,
            type: r.type,
            merchant: r.merchant,
            categoryId: r.categoryId,
            author: me,
            owner: r.type == TxType.income ? '' : r.owner,
          ).toJson()));
          made++;
        }
        done = Recurring.monthKey(m);
      }
      if (done != r.done) {
        unawaited(_hh.update({FieldPath(['recurring', r.id, 'done']): done}));
      }
    }
    return made;
  }
}
