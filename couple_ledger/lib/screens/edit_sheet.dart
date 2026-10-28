import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/transaction.dart';
import '../parser/card_sms_parser.dart';
import '../store/ledger_store.dart';
import 'category_chips.dart';

Future<void> showEditSheet(BuildContext context, {Transaction? existing}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => ChangeNotifierProvider.value(
      value: context.read<LedgerStore>(),
      child: _EditSheet(existing: existing),
    ),
  );
}

class _EditSheet extends StatefulWidget {
  final Transaction? existing;
  const _EditSheet({this.existing});

  @override
  State<_EditSheet> createState() => _EditSheetState();
}

class _EditSheetState extends State<_EditSheet> {
  late TxType _type;
  late DateTime _date;
  late String _category;
  late final TextEditingController _amount;
  late final TextEditingController _merchant;
  late final TextEditingController _memo;
  String _card = '';
  String _owner = ''; // 빈 문자열이면 공용
  bool _categoryTouched = false;

  @override
  void initState() {
    super.initState();
    final t = widget.existing;
    _type = t?.type ?? TxType.expense;
    _date = t?.date ?? DateTime.now();
    _category = t?.categoryId ?? 'etc';
    _card = t?.card ?? '';
    _owner = t?.owner ?? '';
    _amount = TextEditingController(text: t == null ? '' : t.amount.toString());
    _merchant = TextEditingController(text: t?.merchant ?? '');
    _memo = TextEditingController(text: t?.memo ?? '');
    _categoryTouched = t != null;
  }

  @override
  void dispose() {
    _amount.dispose();
    _merchant.dispose();
    _memo.dispose();
    super.dispose();
  }

  Future<void> _pasteSms() async {
    final c = TextEditingController();
    final text = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('카드 문자 붙여넣기'),
        content: TextField(
          controller: c,
          maxLines: 6,
          decoration: const InputDecoration(hintText: '결제 문자 내용을 붙여넣으세요'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, c.text), child: const Text('분석')),
        ],
      ),
    );
    if (text == null) return;
    final many = CardSmsParser.parseMany(text);
    if (many.length > 1) {
      await _importMany(many);
      return;
    }
    final p = many.isNotEmpty ? many.first : CardSmsParser.parse(text);
    if (!mounted) return;
    if (p == null) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('결제 문자로 인식하지 못했어요')));
      return;
    }
    setState(() {
      _type = TxType.expense;
      _amount.text = p.amount.toString();
      _merchant.text = p.merchant;
      _date = p.date;
      _card = p.card;
      _category = context.read<LedgerStore>().categoryFor(p.merchant);
    });
  }

  /// 카톡 대화 등에서 찾은 여러 건의 과거 결제를 한꺼번에 가져온다.
  Future<void> _importMany(List<ParsedPayment> list) async {
    final total = list.fold<int>(0, (s, p) => s + (p.canceled ? 0 : p.amount));
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('결제 ${list.length}건을 찾았어요'),
        content: Text('합계 ${total.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',')}원\n'
            '이미 있는 내역은 건너뛰고 가져옵니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('가져오기')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final store = context.read<LedgerStore>();
    final messenger = ScaffoldMessenger.of(context);
    var added = 0;
    // 오래된 순으로 넣어서 취소 건이 해당 승인 건을 찾을 수 있게 한다
    final sorted = [...list]..sort((a, b) => a.date.compareTo(b.date));
    for (final p in sorted) {
      if (p.canceled) {
        await store.cancelMatching(p.amount, p.merchant, p.date);
      } else if (await store.addIfNew(
          p.toTransaction(
            id: store.newId(),
            author: store.me,
            categoryId: store.categoryFor(p.merchant)))) {
        added++;
      }
    }
    if (!mounted) return;
    Navigator.pop(context);
    messenger.showSnackBar(SnackBar(content: Text('$added건을 가져왔어요')));
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (d != null) {
      setState(() => _date = DateTime(d.year, d.month, d.day, _date.hour, _date.minute));
    }
  }

  Future<void> _delete() async {
    final old = widget.existing!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('내역을 삭제할까요?'),
        content: Text('${old.merchant} · ${old.amount}원\n배우자 화면에서도 함께 사라져요.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('삭제')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final store = context.read<LedgerStore>();
    final messenger = ScaffoldMessenger.of(context);
    await store.remove(old.id);
    if (!mounted) return;
    Navigator.pop(context);
    messenger.showSnackBar(SnackBar(
      content: Text('${old.merchant} 내역을 삭제했어요'),
      action: SnackBarAction(label: '실행 취소', onPressed: () => store.add(old)),
    ));
  }

  Future<void> _save() async {
    final amount = int.tryParse(_amount.text.replaceAll(',', ''));
    if (amount == null || amount <= 0 || _merchant.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('금액과 내용을 입력하세요')));
      return;
    }
    final store = context.read<LedgerStore>();
    final messenger = ScaffoldMessenger.of(context);
    final old = widget.existing;
    final merchant = _merchant.text.trim();
    await store.learnCategory(merchant, _category);
    if (old == null) {
      await store.add(Transaction(
        id: store.newId(),
        date: _date,
        amount: amount,
        type: _type,
        merchant: _merchant.text.trim(),
        categoryId: _category,
        card: _card,
        author: store.me,
        owner: _type == TxType.income ? '' : _owner,
        memo: _memo.text.trim(),
      ));
    } else {
      await store.update(old.copyWith(
        date: _date,
        amount: amount,
        type: _type,
        merchant: _merchant.text.trim(),
        categoryId: _category,
        card: _card,
        owner: _type == TxType.income ? '' : _owner,
        memo: _memo.text.trim(),
      ));
      // 카테고리를 바꿨으면 같은 가맹점의 예전 내역도 한꺼번에 바꿀 수 있게 한다
      if (old.categoryId != _category) {
        final others = store.sameMerchant(merchant, old.categoryId, except: old.id);
        if (others > 0) {
          final to = _category;
          messenger.showSnackBar(SnackBar(
            content: Text('같은 가맹점 내역 $others건도 ${categoryOf(to).name}(으)로 바꿀까요?'),
            action: SnackBarAction(
              label: '모두 바꾸기',
              onPressed: () => store.recategorize(merchant, old.categoryId, to),
            ),
          ));
        }
      }
    }
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<LedgerStore>();
    final spouse = store.spouse;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: SegmentedButton<TxType>(
                segments: const [
                  ButtonSegment(value: TxType.expense, label: Text('지출')),
                  ButtonSegment(value: TxType.income, label: Text('수입')),
                ],
                selected: {_type},
                onSelectionChanged: (s) => setState(() {
                  _type = s.first;
                  // 지출↔수입을 바꾸면 그 종류의 카테고리로 다시 고른다
                  if (categoryOf(_category).isIncome != (_type == TxType.income)) {
                    _category = store.categoryFor(_merchant.text, type: _type);
                  }
                }),
              ),
            ),
            const SizedBox(width: 8),
            if (widget.existing == null)
              IconButton.filledTonal(
                tooltip: '카드 문자 붙여넣기',
                onPressed: _pasteSms,
                icon: const Icon(Icons.sms_outlined),
              ),
          ]),
          const SizedBox(height: 12),
          TextField(
            controller: _amount,
            keyboardType: TextInputType.number,
            autofocus: widget.existing == null,
            decoration: const InputDecoration(labelText: '금액', suffixText: '원', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _merchant,
            decoration: const InputDecoration(labelText: '내용 / 가맹점', border: OutlineInputBorder()),
            onChanged: (v) {
              if (!_categoryTouched) {
                setState(() => _category = store.categoryFor(v, type: _type));
              }
            },
          ),
          const SizedBox(height: 12),
          if (_type == TxType.expense) ...[
            // 누가 썼는지: 나/배우자는 그 사람 용돈에서 차감되고,
            // 기타비용(제3자)은 예산과 용돈 어디에도 잡히지 않는다
            SizedBox(
              width: double.infinity,
              child: SegmentedButton<String>(
                segments: [
                  const ButtonSegment(value: '', label: Text('공용')),
                  ButtonSegment(value: store.me, label: const Text('나')),
                  if (spouse != null)
                    ButtonSegment(value: spouse, label: const Text('배우자')),
                  const ButtonSegment(
                      value: Transaction.thirdParty, label: Text('기타비용')),
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
          const SizedBox(height: 12),
          Row(children: [
            OutlinedButton.icon(
              onPressed: _pickDate,
              icon: const Icon(Icons.calendar_today, size: 16),
              label: Text(DateFormat('M월 d일 HH:mm', 'ko_KR').format(_date)),
            ),
            if (_card.isNotEmpty) ...[
              const SizedBox(width: 8),
              Chip(label: Text(_card)),
            ],
          ]),
          const SizedBox(height: 12),
          TextField(
            controller: _memo,
            decoration: const InputDecoration(labelText: '메모', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(onPressed: _save, child: const Text('저장')),
          ),
          if (widget.existing != null)
            SizedBox(
              width: double.infinity,
              child: TextButton.icon(
                onPressed: _delete,
                style: TextButton.styleFrom(
                    foregroundColor: Theme.of(context).colorScheme.error),
                icon: const Icon(Icons.delete_outline),
                label: const Text('이 내역 삭제'),
              ),
            ),
        ]),
      ),
    );
  }
}
