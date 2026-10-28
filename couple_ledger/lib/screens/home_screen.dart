import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../capture/notification_capture.dart';
import '../models/transaction.dart';
import '../store/ledger_store.dart';
import '../store/session.dart';
import 'edit_sheet.dart';
import 'recurring_screen.dart';
import 'search_screen.dart';
import 'tx_tile.dart';

final _won = NumberFormat('#,###', 'ko_KR');
String won(int v) => '${_won.format(v)}원';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);
  bool _captureOn = true;
  _Filter? _filter; // null이면 전체
  final _listKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _syncCapture();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // 앱을 켜 둔 채 날짜가 바뀌어 결제일이 지났을 수 있다
      final store = context.read<LedgerStore>();
      if (store.loaded) store.applyRecurring();
      _syncCapture();
    }
  }

  Future<void> _syncCapture() async {
    if (!NotificationCapture.supported) return;
    final on = await NotificationCapture.isEnabled();
    if (!mounted) return;
    final added = await NotificationCapture.sync(context.read<LedgerStore>());
    if (!mounted) return;
    setState(() => _captureOn = on);
    if (added > 0) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('결제·배당 $added건을 자동으로 추가했어요')));
    }
  }

  void _push(LedgerStore store, Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => ChangeNotifierProvider.value(value: store, child: screen),
      ));

  /// 같은 필터를 다시 누르면 해제한다. 걸면 내역 목록으로 스크롤한다.
  void _toggle(_Filter f) {
    setState(() => _filter = _filter?.key == f.key ? null : f);
    if (_filter == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = _listKey.currentContext;
      if (ctx != null) {
        Scrollable.ensureVisible(ctx,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  void _shift(int d) =>
      setState(() => _month = DateTime(_month.year, _month.month + d));

  @override
  Widget build(BuildContext context) {
    final store = context.watch<LedgerStore>();
    final all = store.inMonth(_month);
    final f = _filter;
    final items = f == null ? all : all.where(f.test).toList();
    final expense = store.total(_month, TxType.expense);
    final income = store.total(_month, TxType.income);
    final cs = Theme.of(context).colorScheme;
    final anonymous = context.watch<Session>().isAnonymous;

    return Scaffold(
      appBar: AppBar(
        // 아이콘이 많으면 가운데 정렬한 월 이동 버튼과 겹치므로 왼쪽에 두고,
        // 자주 안 쓰는 메뉴는 ⋮ 안으로 넣는다
        titleSpacing: 4,
        title: Row(mainAxisSize: MainAxisSize.min, children: [
          IconButton(
              tooltip: '이전 달',
              onPressed: () => _shift(-1),
              icon: const Icon(Icons.chevron_left)),
          Text(DateFormat('yyyy년 M월', 'ko_KR').format(_month)),
          IconButton(
              tooltip: '다음 달',
              onPressed: () => _shift(1),
              icon: const Icon(Icons.chevron_right)),
        ]),
        actions: [
          IconButton(
            tooltip: '검색',
            icon: const Icon(Icons.search),
            onPressed: () => _push(store, const SearchScreen()),
          ),
          PopupMenuButton<VoidCallback>(
            tooltip: '메뉴',
            // 구글 계정을 아직 연결하지 않았으면 점으로 알려 준다
            icon: Badge(
              isLabelVisible: anonymous,
              child: const Icon(Icons.more_vert),
            ),
            onSelected: (run) => run(),
            itemBuilder: (_) => [
              PopupMenuItem(
                value: () => _push(store, const RecurringScreen()),
                child: const ListTile(
                  leading: Icon(Icons.event_repeat),
                  title: Text('고정지출'),
                ),
              ),
              PopupMenuItem(
                value: () => _showInvite(store),
                child: ListTile(
                  leading: Icon(store.memberCount >= 2
                      ? Icons.people
                      : Icons.person_add_alt_1),
                  title: Text(store.memberCount >= 2 ? '초대 코드' : '배우자 초대'),
                ),
              ),
              PopupMenuItem(
                value: _showAccount,
                child: ListTile(
                  leading: Icon(
                    anonymous ? Icons.warning_amber_rounded : Icons.verified_user_outlined,
                    color: anonymous ? cs.error : null,
                  ),
                  title: Text(anonymous ? '구글 계정 연결' : '내 계정'),
                ),
              ),
            ],
          ),
        ],
      ),
      // 필터를 걸면 내역 머리로 스크롤해야 해서, 화면 밖 위젯도 만들어 두는 Column을 쓴다
      body: SingleChildScrollView(
        padding: const EdgeInsets.only(bottom: 96),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (NotificationCapture.supported && !_captureOn)
            MaterialBanner(
              content: const Text('카드 결제 자동입력을 쓰려면 알림 접근을 허용해 주세요.'),
              actions: [
                TextButton(
                    onPressed: NotificationCapture.openSettings,
                    child: const Text('설정 열기')),
              ],
            ),
          _Summary(
            expense: expense,
            income: income,
            budget: store.monthlyBudget,
            onEditBudget: () => _editBudget(store),
            selected: f?.key,
            onTap: (type) => _toggle(_Filter.type(type)),
          ),
          _Allowances(
            store: store,
            month: _month,
            selected: f?.owner,
            onSelect: (o) => _toggle(_Filter.owner(store, o)),
            onEdit: (uid) => _editAllowance(store, uid),
          ),
          _CategoryBars(
            data: store.expenseByCategory(_month),
            budgets: store.categoryBudgets,
            total: expense,
            selected: f?.key,
            onTap: (id) => _toggle(_Filter.category(id)),
          ),
          _IncomeBreakdown(
            data: store.incomeByCategory(_month),
            expense: expense,
            selected: f?.key,
            onGroup: (g) => _toggle(_Filter.group(g)),
            onCategory: (id) => _toggle(_Filter.category(id)),
          ),
          _Trend(
            store: store,
            month: _month,
            onSelect: (m) => setState(() => _month = m),
          ),
          Padding(
            key: _listKey,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Row(children: [
              Text(f == null ? '내역' : '내역 · ${f.label}',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              if (f != null) ...[
                const SizedBox(width: 8),
                Text(won(items.fold(0, (s, t) => s + t.amount)),
                    style: TextStyle(fontSize: 12, color: cs.outline)),
              ],
              const Spacer(),
              if (f?.budgetCategory != null)
                TextButton(
                  onPressed: () => _editCategoryBudget(store, f!.budgetCategory!),
                  child: const Text('예산'),
                ),
              if (f != null)
                TextButton(
                  onPressed: () => setState(() => _filter = null),
                  child: const Text('전체 보기'),
                ),
            ]),
          ),
          if (items.isEmpty)
            Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Text(
                    f != null
                        ? '이 달에는 해당 내역이 없어요.'
                        : '내역이 없어요.\n+ 버튼으로 입력하거나 카드 문자를 붙여넣어 보세요.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: cs.outline)),
              ),
            ),
          ..._grouped(items, store),
        ]),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showEditSheet(context),
        icon: const Icon(Icons.add),
        label: const Text('입력'),
      ),
    );
  }

  List<Widget> _grouped(List<Transaction> items, LedgerStore store) {
    final out = <Widget>[];
    String? lastDay;
    final df = DateFormat('M월 d일 (E)', 'ko_KR');
    for (final t in items) {
      final day = df.format(t.date);
      if (day != lastDay) {
        out.add(Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 2),
          child: Text(day,
              style: TextStyle(
                  fontSize: 12, color: Theme.of(context).colorScheme.outline)),
        ));
        lastDay = day;
      }
      out.add(TxTile(t, store: store));
    }
    return out;
  }

  void _showAccount() {
    final session = context.read<Session>();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(session.isAnonymous ? '구글 계정 연결' : '내 계정'),
        content: Text(session.isAnonymous
            ? '지금은 로그인 없이 쓰는 중이에요.\n'
                '앱을 지우거나 폰을 바꾸면 가계부에 다시 들어갈 수 없어요.\n'
                '구글 계정을 연결하면 어디서든 복구할 수 있어요.'
            : '${session.email ?? "구글 계정"} 으로 연결돼 있어요.'),
        actions: [
          if (session.isAnonymous)
            FilledButton(
              onPressed: () async {
                Navigator.pop(ctx);
                final messenger = ScaffoldMessenger.of(context);
                final err = await session.connectGoogle();
                messenger.showSnackBar(SnackBar(
                    content: Text(err ?? '구글 계정을 연결했어요')));
              },
              child: const Text('구글로 연결'),
            ),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('닫기')),
        ],
      ),
    );
  }

  void _showInvite(LedgerStore store) {
    final paired = store.memberCount >= 2;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(paired ? '함께 쓰는 중이에요' : '배우자 초대'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(paired
              ? '초대 코드 (다른 기기에서 참여할 때)'
              : "배우자 앱에서 '코드로 참여하기'에 아래 코드를 입력하세요"),
          const SizedBox(height: 12),
          SelectableText(store.householdId,
              style: const TextStyle(
                  fontSize: 28, fontWeight: FontWeight.bold, letterSpacing: 4)),
        ]),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: store.householdId));
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context)
                  .showSnackBar(const SnackBar(content: Text('코드를 복사했어요')));
            },
            child: const Text('복사'),
          ),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('닫기')),
        ],
      ),
    );
  }

  /// 금액을 묻는 공통 대화상자. 취소하면 null.
  Future<int?> _askAmount(String title, int initial, {String? hint}) {
    final c = TextEditingController(text: initial > 0 ? initial.toString() : '');
    return showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: c,
          autofocus: true,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(suffixText: '원', helperText: hint),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('취소')),
          FilledButton(
              onPressed: () =>
                  Navigator.pop(ctx, int.tryParse(c.text.replaceAll(',', '')) ?? 0),
              child: const Text('저장')),
        ],
      ),
    );
  }

  Future<void> _editBudget(LedgerStore store) async {
    final v = await _askAmount('월 예산', store.monthlyBudget);
    if (v != null && v > 0) await store.setBudget(v);
  }

  Future<void> _editAllowance(LedgerStore store, String uid) async {
    final v = await _askAmount('${store.ownerLabel(uid)} 월 용돈', store.allowanceOf(uid));
    if (v != null && v >= 0) await store.setAllowance(uid, v);
  }

  Future<void> _editCategoryBudget(LedgerStore store, String id) async {
    final c = categoryOf(id);
    final v = await _askAmount('${c.emoji} ${c.name} 월 예산', store.categoryBudgets[id] ?? 0,
        hint: '비워 두면 예산을 없애요');
    if (v != null) await store.setCategoryBudget(id, v);
  }
}

/// 공용 지출과 각자 용돈 사용 현황. 줄을 누르면 그 사람 내역만 보이고,
/// 연필을 누르면 용돈을 바꾼다.
class _Allowances extends StatelessWidget {
  final LedgerStore store;
  final DateTime month;
  final String? selected;
  final ValueChanged<String> onSelect;
  final ValueChanged<String> onEdit;
  const _Allowances({
    required this.store,
    required this.month,
    required this.selected,
    required this.onSelect,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final people = [store.me, if (store.spouse != null) store.spouse!];
    return Card(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      clipBehavior: Clip.antiAlias,
      child: Column(children: [
        for (final uid in people) _person(context, cs, uid),
        ListTile(
          dense: true,
          selected: selected == '',
          leading: const Icon(Icons.home_outlined),
          title: const Text('공용'),
          trailing: Text(won(store.spentBy(month, '')),
              style: const TextStyle(fontWeight: FontWeight.w600)),
          onTap: () => onSelect(''),
        ),
        ListTile(
          dense: true,
          selected: selected == Transaction.thirdParty,
          leading: const Icon(Icons.person_outline),
          title: const Text('기타비용'),
          subtitle: const Text('제3자 사용 · 예산에서 제외'),
          trailing: Text(won(store.spentBy(month, Transaction.thirdParty)),
              style: TextStyle(fontWeight: FontWeight.w600, color: cs.outline)),
          onTap: () => onSelect(Transaction.thirdParty),
        ),
      ]),
    );
  }

  Widget _person(BuildContext context, ColorScheme cs, String uid) {
    final limit = store.allowanceOf(uid);
    final spent = store.spentBy(month, uid);
    final over = spent > limit;
    final ratio = limit == 0 ? (spent > 0 ? 1.0 : 0.0) : (spent / limit).clamp(0.0, 1.0);
    return InkWell(
      onTap: () => onSelect(uid),
      child: Container(
        color: selected == uid ? cs.primaryContainer.withValues(alpha: 0.4) : null,
        padding: const EdgeInsets.fromLTRB(16, 10, 4, 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('${store.ownerLabel(uid)} 용돈',
                style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(width: 8),
            Text('${won(spent)} / ${won(limit)}',
                style: TextStyle(fontSize: 12, color: cs.outline)),
            const Spacer(),
            Text(over ? '${won(spent - limit)} 초과' : '${won(limit - spent)} 남음',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: over ? cs.error : cs.primary)),
            IconButton(
              tooltip: '용돈 바꾸기',
              visualDensity: VisualDensity.compact,
              iconSize: 18,
              onPressed: () => onEdit(uid),
              icon: const Icon(Icons.edit_outlined),
            ),
          ]),
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 6,
              borderRadius: BorderRadius.circular(3),
              color: over ? cs.error : cs.primary,
            ),
          ),
        ]),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  final int expense, income, budget;
  final VoidCallback onEditBudget;
  final String? selected; // 걸려 있는 필터 key
  final ValueChanged<TxType> onTap;
  const _Summary({
    required this.expense,
    required this.income,
    required this.budget,
    required this.onEditBudget,
    required this.selected,
    required this.onTap,
  });

  /// 누르면 그 종류의 내역만 보인다
  Widget _stat(ColorScheme cs, TxType type, String label, String value, {Color? color}) {
    final on = selected == _Filter.type(type).key;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () => onTap(type),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: on ? cs.primaryContainer.withValues(alpha: 0.5) : null,
          borderRadius: BorderRadius.circular(8),
        ),
        child: _Stat(label, value, color: color),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final ratio = budget == 0 ? 0.0 : (expense / budget).clamp(0.0, 1.0);
    final over = expense > budget;
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: _stat(cs, TxType.expense, '지출', won(expense))),
            const SizedBox(width: 8),
            Expanded(child: _stat(cs, TxType.income, '수입', won(income), color: Colors.blue)),
          ]),
          const SizedBox(height: 16),
          InkWell(
            onTap: onEditBudget,
            child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('예산 ${won(budget)}', style: const TextStyle(fontSize: 12)),
              Text(over ? '${won(expense - budget)} 초과' : '${won(budget - expense)} 남음',
                  style: TextStyle(fontSize: 12, color: over ? cs.error : cs.primary)),
            ]),
          ),
          const SizedBox(height: 6),
          LinearProgressIndicator(
            value: ratio,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
            color: over ? cs.error : cs.primary,
          ),
        ]),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final String label, value;
  final Color? color;
  const _Stat(this.label, this.value, {this.color});

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.outline)),
        Text(value,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
      ]);
}

/// 카테고리별 지출. 예산을 정한 카테고리는 예산 대비, 아니면 전체 지출 대비 비율로 막대를 그린다.
/// 줄을 누르면 그 카테고리 내역만 보이고, 내역 머리의 '예산'으로 예산을 정한다.
class _CategoryBars extends StatefulWidget {
  final Map<String, int> data;
  final Map<String, int> budgets;
  final int total;
  final String? selected; // 걸려 있는 필터 key
  final ValueChanged<String> onTap;
  const _CategoryBars({
    required this.data,
    required this.budgets,
    required this.total,
    required this.selected,
    required this.onTap,
  });

  @override
  State<_CategoryBars> createState() => _CategoryBarsState();
}

class _CategoryBarsState extends State<_CategoryBars> {
  static const _collapsed = 5;
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final data = widget.data, budgets = widget.budgets;
    if (data.isEmpty && budgets.isEmpty) return const SizedBox.shrink();
    final cs = Theme.of(context).colorScheme;

    // 펼치면 모든 지출 카테고리를 보여 줘서 아직 안 쓴 카테고리에도 예산을 정할 수 있게 한다
    final ids = _expanded
        ? expenseCategories.map((c) => c.id).toList()
        : {...data.keys, ...budgets.keys}.toList();
    ids.sort((a, b) => (data[b] ?? 0).compareTo(data[a] ?? 0));
    final shown = _expanded ? ids : ids.take(_collapsed).toList();
    final hidden = expenseCategories.length - shown.length;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(children: [
        for (final id in shown) _row(cs, id, data[id] ?? 0, budgets[id]),
        if (hidden > 0 || _expanded)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => setState(() => _expanded = !_expanded),
              child: Text(_expanded ? '접기' : '카테고리 더보기'),
            ),
          ),
      ]),
    );
  }

  Widget _row(ColorScheme cs, String id, int spent, int? budget) {
    final c = categoryOf(id);
    final over = budget != null && spent > budget;
    final double ratio;
    final Color color;
    if (budget != null) {
      ratio = budget == 0 ? 1 : (spent / budget).clamp(0.0, 1.0);
      color = over ? cs.error : cs.primary;
    } else {
      ratio = widget.total == 0 ? 0 : spent / widget.total;
      color = cs.primary.withValues(alpha: 0.45);
    }
    final small = TextStyle(fontSize: 11, color: over ? cs.error : cs.outline);
    final on = widget.selected == _Filter.category(id).key;
    return InkWell(
      borderRadius: BorderRadius.circular(6),
      onTap: () => widget.onTap(id),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 4),
        decoration: BoxDecoration(
          color: on ? cs.primaryContainer.withValues(alpha: 0.5) : null,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(children: [
          SizedBox(
              width: 92,
              child: Text('${c.emoji} ${c.name}', style: const TextStyle(fontSize: 12))),
          Expanded(
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 6,
              borderRadius: BorderRadius.circular(3),
              color: color,
            ),
          ),
          SizedBox(
            width: 96,
            child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(won(spent), style: const TextStyle(fontSize: 12)),
              if (budget != null)
                Text(
                    over
                        ? '${_short(spent - budget)} 초과'
                        : '${_short(budget - spent)} 남음',
                    style: small),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// 수입을 고정/투자/기타 그룹으로 나눠 비율 막대와 함께 보여 준다.
class _IncomeBreakdown extends StatelessWidget {
  final Map<String, int> data;
  final int expense;
  final String? selected; // 걸려 있는 필터 key
  final ValueChanged<IncomeGroup> onGroup;
  final ValueChanged<String> onCategory;
  const _IncomeBreakdown({
    required this.data,
    required this.expense,
    required this.selected,
    required this.onGroup,
    required this.onCategory,
  });

  /// 누를 수 있는 줄. 필터가 걸려 있으면 배경을 칠한다.
  Widget _tappable(ColorScheme cs, String key, VoidCallback onTap, Widget child) =>
      InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            color: selected == key ? cs.primaryContainer.withValues(alpha: 0.5) : null,
            borderRadius: BorderRadius.circular(6),
          ),
          child: child,
        ),
      );

  static Color colorOf(IncomeGroup g) => switch (g) {
        IncomeGroup.fixed => Colors.blue,
        IncomeGroup.invest => Colors.teal,
        IncomeGroup.other => Colors.amber.shade700,
      };

  @override
  Widget build(BuildContext context) {
    final total = data.values.fold(0, (a, b) => a + b);
    if (total == 0) return const SizedBox.shrink();
    final cs = Theme.of(context).colorScheme;
    final byGroup = {
      for (final g in IncomeGroup.values)
        g: incomeCategories
            .where((c) => c.group == g)
            .fold(0, (s, c) => s + (data[c.id] ?? 0)),
    };
    final groups = IncomeGroup.values.where((g) => byGroup[g]! > 0).toList();
    final fixed = byGroup[IncomeGroup.fixed]!;

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Text('수입 구성', style: TextStyle(fontWeight: FontWeight.bold)),
            const Spacer(),
            Text(won(total),
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.blue)),
          ]),
          const SizedBox(height: 10),
          // 그룹 비율을 한 줄 막대로
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              height: 10,
              child: Row(children: [
                for (final g in groups)
                  Expanded(flex: byGroup[g]!, child: Container(color: colorOf(g))),
              ]),
            ),
          ),
          const SizedBox(height: 8),
          for (final g in groups) ..._group(cs, g, byGroup[g]!, total),
          if (fixed > 0 && expense > 0) ...[
            const Divider(height: 20),
            Text(
              expense <= fixed
                  ? '고정수입의 ${(expense * 100 / fixed).round()}%를 썼어요 · ${won(fixed - expense)} 남음'
                  : '고정수입보다 ${won(expense - fixed)} 더 썼어요',
              style: TextStyle(
                  fontSize: 12, color: expense <= fixed ? cs.outline : cs.error),
            ),
          ],
        ]),
      ),
    );
  }

  List<Widget> _group(ColorScheme cs, IncomeGroup g, int sum, int total) {
    final cats = incomeCategories
        .where((c) => c.group == g && (data[c.id] ?? 0) > 0)
        .toList()
      ..sort((a, b) => data[b.id]!.compareTo(data[a.id]!));
    final small = TextStyle(fontSize: 12, color: cs.outline);
    return [
      _tappable(cs, _Filter.group(g).key, () => onGroup(g), Padding(
        padding: const EdgeInsets.fromLTRB(4, 5, 4, 3),
        child: Row(children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: colorOf(g), shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(g.label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          const SizedBox(width: 6),
          Text('${(sum * 100 / total).round()}%', style: small),
          const Spacer(),
          Text(won(sum), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ]),
      )),
      // 하위 카테고리가 하나뿐이면 그룹 줄과 같은 내용이라 생략한다
      if (cats.length > 1 || cats.length == 1 && cats.first.name != g.label)
        for (final c in cats)
          _tappable(cs, _Filter.category(c.id).key, () => onCategory(c.id), Padding(
            padding: const EdgeInsets.fromLTRB(22, 3, 4, 3),
            child: Row(children: [
              Text('${c.emoji} ${c.name}', style: small),
              const Spacer(),
              Text(won(data[c.id]!), style: small),
            ]),
          )),
    ];
  }
}

/// 만 원 단위 짧은 표기 (막대 위 라벨용): 1,234,000 → "123만"
String _short(int v) {
  if (v >= 100000000) return '${(v / 100000000).toStringAsFixed(1)}억';
  if (v >= 10000) return '${(v / 10000).round()}만';
  return won(v);
}

/// 최근 6개월 지출 추이와 지난달 대비 변화. 막대를 누르면 그 달로 이동한다.
class _Trend extends StatelessWidget {
  final LedgerStore store;
  final DateTime month;
  final ValueChanged<DateTime> onSelect;
  const _Trend({required this.store, required this.month, required this.onSelect});

  static const _n = 6;
  static const _barMax = 96.0;

  @override
  Widget build(BuildContext context) {
    final values = store.monthlyExpense(month, _n);
    final peak = values.fold(0, (a, b) => a > b ? a : b);
    if (peak == 0) return const SizedBox.shrink();
    final cs = Theme.of(context).colorScheme;
    final months = [for (var i = _n - 1; i >= 0; i--) DateTime(month.year, month.month - i)];

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('월별 지출', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          _comparison(context, cs, values),
          const SizedBox(height: 12),
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            for (var i = 0; i < _n; i++)
              Expanded(child: _bar(context, cs, months[i], values[i], peak, i == _n - 1)),
          ]),
        ]),
      ),
    );
  }

  Widget _bar(BuildContext context, ColorScheme cs, DateTime m, int v, int peak, bool selected) {
    final h = v == 0 ? 0.0 : (v / peak * _barMax).clamp(4.0, _barMax);
    return Tooltip(
      message: '${m.month}월 ${won(v)}',
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => onSelect(m),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            // 값 라벨은 선택한 달에만 붙인다
            SizedBox(
              height: 16,
              child: selected
                  ? Text(_short(v),
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600))
                  : null,
            ),
            const SizedBox(height: 2),
            Container(
              height: h,
              decoration: BoxDecoration(
                color: selected ? cs.primary : cs.primary.withValues(alpha: 0.3),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
              ),
            ),
            Container(height: 1, color: cs.outlineVariant),
            const SizedBox(height: 4),
            Text('${m.month}월',
                style: TextStyle(
                  fontSize: 11,
                  color: selected ? cs.onSurface : cs.outline,
                  fontWeight: selected ? FontWeight.w600 : null,
                )),
          ]),
        ),
      ),
    );
  }

  /// "지난달보다 12만 원 더 썼어요 · 가장 많이 는 곳: 식비 +8만"
  Widget _comparison(BuildContext context, ColorScheme cs, List<int> values) {
    final cur = values[_n - 1];
    final prev = values[_n - 2];
    final style = TextStyle(fontSize: 12, color: cs.outline);
    if (prev == 0) return Text('지난달 기록이 없어요', style: style);
    final diff = cur - prev;
    final head = diff == 0
        ? '지난달과 같아요'
        : '지난달보다 ${won(diff.abs())} ${diff > 0 ? '더' : '덜'} 썼어요';

    final now = store.expenseByCategory(month);
    final before = store.expenseByCategory(DateTime(month.year, month.month - 1));
    String? topId;
    var topDiff = 0;
    for (final id in {...now.keys, ...before.keys}) {
      final d = (now[id] ?? 0) - (before[id] ?? 0);
      if (d > topDiff) {
        topDiff = d;
        topId = id;
      }
    }
    return Text.rich(TextSpan(style: style, children: [
      TextSpan(
          text: head,
          style: TextStyle(color: diff > 0 ? cs.error : cs.primary, fontWeight: FontWeight.w600)),
      if (topId != null && diff != 0)
        TextSpan(text: ' · ${categoryOf(topId).name} +${_short(topDiff)}'),
    ]));
  }
}

/// 내역 목록 필터. 요약·용돈·카테고리 줄을 누르면 하나씩 걸린다.
class _Filter {
  final String key; // 같은 필터를 다시 누르면 해제하려고 비교한다
  final String label;
  final bool Function(Transaction) test;
  final String? owner; // 용돈 줄 강조용
  final String? budgetCategory; // 지출 카테고리면 내역 머리에 예산 버튼을 둔다

  const _Filter._(this.key, this.label, this.test, {this.owner, this.budgetCategory});

  factory _Filter.type(TxType type) => _Filter._(
      'type:${type.name}', type == TxType.income ? '수입' : '지출', (t) => t.type == type);

  factory _Filter.owner(LedgerStore store, String owner) => _Filter._(
      'owner:$owner',
      store.ownerLabel(owner),
      (t) => t.type == TxType.expense && t.owner == owner,
      owner: owner);

  factory _Filter.category(String id) {
    final c = categoryOf(id);
    return _Filter._('cat:$id', '${c.emoji} ${c.name}', (t) => t.categoryId == id,
        budgetCategory: c.isIncome ? null : id);
  }

  factory _Filter.group(IncomeGroup g) => _Filter._('group:${g.name}', g.label,
      (t) => t.type == TxType.income && categoryOf(t.categoryId).group == g);
}
