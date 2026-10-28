import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/transaction.dart';
import '../store/ledger_store.dart';
import 'home_screen.dart' show won;
import 'tx_tile.dart';

enum _Period { thisMonth, last3, thisYear, lastYear, all, custom }

const _periodLabels = {
  _Period.thisMonth: '이번 달',
  _Period.last3: '최근 3개월',
  _Period.thisYear: '올해',
  _Period.lastYear: '작년',
  _Period.all: '전체',
  _Period.custom: '직접 선택',
};

/// 검색어와 기간, 카테고리로 내역을 찾고 합계를 보여준다.
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _query = TextEditingController();
  _Period _period = _Period.thisYear;
  DateTimeRange? _custom;
  String? _category;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  /// [from] 이상 [to] 미만. 전체면 둘 다 null.
  (DateTime?, DateTime?) get _range {
    final now = DateTime.now();
    return switch (_period) {
      _Period.thisMonth => (DateTime(now.year, now.month), DateTime(now.year, now.month + 1)),
      _Period.last3 => (DateTime(now.year, now.month - 2), DateTime(now.year, now.month + 1)),
      _Period.thisYear => (DateTime(now.year), DateTime(now.year + 1)),
      _Period.lastYear => (DateTime(now.year - 1), DateTime(now.year)),
      _Period.all => (null, null),
      _Period.custom => _custom == null
          ? (null, null)
          : (_custom!.start, _custom!.end.add(const Duration(days: 1))),
    };
  }

  Future<void> _pickRange() async {
    final now = DateTime.now();
    final r = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(now.year, now.month, now.day),
      initialDateRange: _custom,
    );
    if (r != null) {
      setState(() {
        _custom = r;
        _period = _Period.custom;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<LedgerStore>();
    final cs = Theme.of(context).colorScheme;
    final (from, to) = _range;
    final results = store.search(
      query: _query.text,
      from: from,
      to: to,
      categoryId: _category,
    );
    final expense = results
        .where((t) => t.type == TxType.expense)
        .fold(0, (s, t) => s + t.amount);
    final income = results
        .where((t) => t.type == TxType.income)
        .fold(0, (s, t) => s + t.amount);
    final df = DateFormat('yy.M.d', 'ko_KR');

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _query,
          autofocus: true,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            hintText: '가맹점, 메모, 카드 검색',
            border: InputBorder.none,
            suffixIcon: _query.text.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(_query.clear),
                  ),
          ),
          onChanged: (_) => setState(() {}),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(children: [
              for (final p in _Period.values)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ChoiceChip(
                    label: Text(p == _Period.custom && _custom != null
                        ? '${df.format(_custom!.start)}~${df.format(_custom!.end)}'
                        : _periodLabels[p]!),
                    selected: _period == p,
                    onSelected: (_) => p == _Period.custom
                        ? _pickRange()
                        : setState(() => _period = p),
                  ),
                ),
            ]),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Row(children: [
              for (final c in categories)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: FilterChip(
                    label: Text('${c.emoji} ${c.name}'),
                    selected: _category == c.id,
                    onSelected: (_) =>
                        setState(() => _category = _category == c.id ? null : c.id),
                  ),
                ),
            ]),
          ),
          Card(
            margin: const EdgeInsets.all(16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(children: [
                Expanded(child: _Sum('건수', '${results.length}건')),
                Expanded(child: _Sum('지출', won(expense))),
                Expanded(child: _Sum('수입', won(income), color: Colors.blue)),
              ]),
            ),
          ),
          if (results.isEmpty)
            Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Text('조건에 맞는 내역이 없어요',
                    style: TextStyle(color: cs.outline)),
              ),
            ),
          for (final t in results) TxTile(t, store: store, showDate: true),
        ],
      ),
    );
  }
}

class _Sum extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  const _Sum(this.label, this.value, {this.color});

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.outline)),
        Text(value,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
      ]);
}
