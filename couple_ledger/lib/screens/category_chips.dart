import 'package:flutter/material.dart';

import '../models/transaction.dart';

/// 카테고리 선택 칩. 수입은 고정/투자/기타 그룹별로 나눠 보여 준다.
class CategoryChips extends StatelessWidget {
  final TxType type;
  final String selected;
  final ValueChanged<String> onSelected;
  const CategoryChips({
    super.key,
    required this.type,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (type == TxType.expense) return _wrap(expenseCategories);
    final style = TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.outline);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      for (final g in IncomeGroup.values) ...[
        Padding(
          padding: const EdgeInsets.only(top: 4, bottom: 4),
          child: Text(g.label, style: style),
        ),
        _wrap(incomeCategories.where((c) => c.group == g)),
      ],
    ]);
  }

  Widget _wrap(Iterable<Category> cats) => Wrap(spacing: 6, runSpacing: 6, children: [
        for (final c in cats)
          ChoiceChip(
            label: Text('${c.emoji} ${c.name}'),
            selected: selected == c.id,
            onSelected: (_) => onSelected(c.id),
          ),
      ]);
}
