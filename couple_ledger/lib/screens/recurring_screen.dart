import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/recurring.dart';
import '../models/transaction.dart';
import '../store/ledger_store.dart';
import 'category_chips.dart';
import 'home_screen.dart' show won;

/// 고정지출/고정수입 목록. 등록해 두면 매달 결제일에 내역이 자동으로 들어간다.
class RecurringScreen extends StatelessWidget {
  const RecurringScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<LedgerStore>();
    final list = store.recurring;
    final cs = Theme.of(context).colorScheme;
    final monthly = list
        .where((r) => r.type == TxType.expense && r.owner != Transaction.thirdParty)
        .fold(0, (s, r) => s + r.amount);
    return Scaffold(
      appBar: AppBar(title: const Text('고정지출')),
      body: list.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text('월세, 관리비, 통신비, 구독료처럼\n매달 나가는 돈을 등록해 두면\n결제일에 자동으로 기록돼요.',
                    textAlign: TextAlign.center, style: TextStyle(color: cs.outline)),
              ),
            )
          : ListView(
              padding: const EdgeInsets.only(bottom: 96),
              children: [
                ListTile(
                  title: const Text('매달 고정지출'),
                  trailing: Text(won(monthly),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ),
                const Divider(height: 1),
                for (final r in list)
                  Dismissible(
                    key: ValueKey(r.id),
                    direction: DismissDirection.endToStart,
                    background: Container(
                      color: Colors.red,
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.only(right: 20),
                      child: const Icon(Icons.delete, color: Colors.white),
                    ),
                    onDismissed: (_) {
                      store.removeRecurring(r.id);
                      ScaffoldMessenger.of(context)
                        ..clearSnackBars()
                        ..showSnackBar(SnackBar(
                          content: Text('${r.merchant} 고정지출을 지웠어요 (이미 들어간 내역은 그대로예요)'),
                          action: SnackBarAction(
                              label: '실행 취소', onPressed: () => store.saveRecurring(r)),
                        ));
                    },
                    child: ListTile(
                      leading: CircleAvatar(child: Text(categoryOf(r.categoryId).emoji)),
                      title: Text(r.merchant),
                      subtitle: Text([
                        '매달 ${r.day}일',
                        categoryOf(r.categoryId).name,
                        if (r.type == TxType.expense) store.ownerLabel(r.owner),
                      ].join(' · ')),
                      trailing: Text(
                        '${r.type == TxType.expense ? '-' : '+'}${won(r.amount)}',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: r.type == TxType.income ? Colors.blue : null,
                        ),
                      ),
                      onTap: () => _showForm(context, existing: r),
                    ),
                  ),
              ],
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showForm(context),
        icon: const Icon(Icons.add),
        label: const Text('추가'),
      ),
    );
  }

  void _showForm(BuildContext context, {Recurring? existing}) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<LedgerStore>(),
        child: _RecurringForm(existing: existing),
      ),
    );
  }
}

class _RecurringForm extends StatefulWidget {
  final Recurring? existing;
  const _RecurringForm({this.existing});

  @override
  State<_RecurringForm> createState() => _RecurringFormState();
}

class _RecurringFormState extends State<_RecurringForm> {
  late TxType _type;
  late int _day;
  late String _category;
  late String _owner;
  late final TextEditingController _merchant;
  late final TextEditingController _amount;
  bool _categoryTouched = false;
  bool _includeThisMonth = true;

  @override
  void initState() {
    super.initState();
    final r = widget.existing;
    _type = r?.type ?? TxType.expense;
    _day = r?.day ?? DateTime.now().day;
    _category = r?.categoryId ?? 'housing';
    _owner = r?.owner ?? '';
    _merchant = TextEditingController(text: r?.merchant ?? '');
    _amount = TextEditingController(text: r == null ? '' : r.amount.toString());
    _categoryTouched = r != null;
  }

  @override
  void dispose() {
    _merchant.dispose();
    _amount.dispose();
    super.dispose();
  }

  /// 새로 등록하는데 이번 달 결제일이 이미 지났는지
  bool get _dayPassed {
    final now = DateTime.now();
    final probe = Recurring(
        id: '', merchant: '', amount: 0, type: _type, categoryId: '', day: _day, done: '');
    return !probe.dateIn(DateTime(now.year, now.month)).isAfter(now);
  }

  void _save() {
    final amount = int.tryParse(_amount.text.replaceAll(',', ''));
    final merchant = _merchant.text.trim();
    if (amount == null || amount <= 0 || merchant.isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('이름과 금액을 입력하세요')));
      return;
    }
    final store = context.read<LedgerStore>();
    final now = DateTime.now();
    final thisMonth = DateTime(now.year, now.month);
    // done = 이미 처리한 것으로 칠 마지막 달. 이번 달 것을 넣으려면 지난달로 둔다.
    // 수정 중에 다른 기기가 done을 올렸을 수 있으니 최신 값을 쓴다
    final latest = store.recurring.where((r) => r.id == widget.existing?.id);
    final done = latest.isNotEmpty
        ? latest.first.done
        : Recurring.monthKey(_dayPassed && !_includeThisMonth
            ? thisMonth
            : DateTime(now.year, now.month - 1));
    store.saveRecurring(Recurring(
      id: widget.existing?.id ?? store.newId(),
      merchant: merchant,
      amount: amount,
      type: _type,
      categoryId: _category,
      owner: _type == TxType.income ? '' : _owner,
      day: _day,
      done: done,
    ));
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<LedgerStore>();
    final spouse = store.spouse;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(
            width: double.infinity,
            child: SegmentedButton<TxType>(
              segments: const [
                ButtonSegment(value: TxType.expense, label: Text('고정지출')),
                ButtonSegment(value: TxType.income, label: Text('고정수입')),
              ],
              selected: {_type},
              onSelectionChanged: (s) => setState(() {
                _type = s.first;
                if (categoryOf(_category).isIncome != (_type == TxType.income)) {
                  _category = _type == TxType.income
                      ? store.categoryFor(_merchant.text, type: _type)
                      : 'housing';
                }
              }),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _merchant,
            autofocus: widget.existing == null,
            decoration: const InputDecoration(
                labelText: '이름 (예: 월세, 넷플릭스)', border: OutlineInputBorder()),
            onChanged: (v) {
              if (!_categoryTouched) {
                final c = store.categoryFor(v, type: _type);
                if (c != 'etc') setState(() => _category = c);
              }
            },
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _amount,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: '금액', suffixText: '원', border: OutlineInputBorder()),
              ),
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: 120,
              child: DropdownButtonFormField<int>(
                value: _day,
                decoration: const InputDecoration(labelText: '매달', border: OutlineInputBorder()),
                items: [
                  for (var d = 1; d <= 31; d++)
                    DropdownMenuItem(value: d, child: Text(d == 31 ? '말일' : '$d일')),
                ],
                onChanged: (v) => setState(() => _day = v!),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          if (_type == TxType.expense) ...[
            SizedBox(
              width: double.infinity,
              child: SegmentedButton<String>(
                segments: [
                  const ButtonSegment(value: '', label: Text('공용')),
                  ButtonSegment(value: store.me, label: const Text('나')),
                  if (spouse != null) ButtonSegment(value: spouse, label: const Text('배우자')),
                  const ButtonSegment(value: Transaction.thirdParty, label: Text('기타비용')),
                ],
                selected: {_owner},
                showSelectedIcon: false,
                onSelectionChanged: (s) => setState(() => _owner = s.first),
              ),
            ),
            const SizedBox(height: 12),
          ],
          CategoryChips(
            type: _type,
            selected: _category,
            onSelected: (id) => setState(() {
              _category = id;
              _categoryTouched = true;
            }),
          ),
          const SizedBox(height: 4),
          if (widget.existing == null && _dayPassed)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('이번 달 것도 지금 기록'),
              subtitle: const Text('이번 달 결제일이 이미 지났어요. 이미 입력했다면 끄세요.'),
              value: _includeThisMonth,
              onChanged: (v) => setState(() => _includeThisMonth = v),
            ),
          if (widget.existing != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('바꾼 내용은 다음 결제일부터 적용돼요.',
                  style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.outline)),
            ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(onPressed: _save, child: const Text('저장')),
          ),
        ]),
      ),
    );
  }
}
