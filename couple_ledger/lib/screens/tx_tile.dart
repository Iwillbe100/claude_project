import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/transaction.dart';
import '../store/ledger_store.dart';
import 'edit_sheet.dart';
import 'home_screen.dart' show won;

/// 내역 한 줄. 누르면 수정, 왼쪽으로 밀면 삭제(실행 취소 가능).
class TxTile extends StatelessWidget {
  final Transaction t;
  final LedgerStore store;
  final bool showDate; // 날짜 머리글 없이 나열할 때 (검색 결과)
  const TxTile(this.t, {super.key, required this.store, this.showDate = false});

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: ValueKey(t.id),
      direction: DismissDirection.endToStart,
      background: Container(
        color: Colors.red,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      onDismissed: (_) {
        store.remove(t.id);
        ScaffoldMessenger.of(context)
          ..clearSnackBars()
          ..showSnackBar(SnackBar(
            content: Text('${t.merchant} 내역을 삭제했어요'),
            action: SnackBarAction(label: '실행 취소', onPressed: () => store.add(t)),
          ));
      },
      child: ListTile(
        leading: CircleAvatar(child: Text(categoryOf(t.categoryId).emoji)),
        title: Text(t.merchant),
        subtitle: Text([
          if (showDate) DateFormat('yy.M.d', 'ko_KR').format(t.date),
          categoryOf(t.categoryId).name,
          if (t.type == TxType.expense) store.ownerLabel(t.owner),
          if (t.card.isNotEmpty) t.card,
          if (t.auto) '자동',
          if (t.id.startsWith('rec_')) '고정',
        ].join(' · ')),
        trailing: Text(
          '${t.type == TxType.expense ? '-' : '+'}${won(t.amount)}',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: t.type == TxType.income
                ? Colors.blue
                : t.excluded
                    ? Theme.of(context).colorScheme.outline
                    : null,
          ),
        ),
        onTap: () => showEditSheet(context, existing: t),
      ),
    );
  }
}
