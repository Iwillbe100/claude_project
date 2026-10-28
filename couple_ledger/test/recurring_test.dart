import 'package:couple_ledger/models/recurring.dart';
import 'package:couple_ledger/models/transaction.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('가맹점 대표 이름', () {
    expect(merchantKey('스타벅스 강남점'), merchantKey('스타벅스 역삼점'));
    expect(merchantKey('쿠팡(쿠페이)'), '쿠팡');
    expect(merchantKey('(주)이마트 성수'), '이마트');
    expect(merchantKey('gs25 논현점'), 'GS25');
  });

  Recurring rent(int day, String done) => Recurring(
        id: 'r1',
        merchant: '월세',
        amount: 500000,
        type: TxType.expense,
        categoryId: 'housing',
        day: day,
        done: done,
      );

  test('그 달에 없는 날이면 말일', () {
    expect(rent(31, '202601').dateIn(DateTime(2026, 2)).day, 28);
    expect(rent(31, '202601').dateIn(DateTime(2028, 2)).day, 29);
    expect(rent(31, '202601').dateIn(DateTime(2026, 3)).day, 31);
    expect(rent(15, '202601').dateIn(DateTime(2026, 4)).day, 15);
  });

  test('달 키와 거래 id', () {
    expect(Recurring.monthKey(DateTime(2026, 3)), '202603');
    expect(Recurring.parseMonth('202612'), DateTime(2026, 12));
    expect(rent(1, '202601').txId(DateTime(2026, 3)), 'rec_r1_202603');
  });

  test('쿠팡 카테고리', () {
    expect(guessCategory('쿠팡(쿠페이)'), 'coupang');
    expect(guessCategory('COUPANG'), 'coupang');
    expect(guessCategory('쿠팡이츠'), 'food');
    expect(categoryOf('없는카테고리').id, 'etc');
  });

  test('수입 카테고리 추정과 그룹', () {
    expect(guessIncomeCategory('10월 월급'), 'salary');
    expect(guessIncomeCategory('삼성전자 배당'), 'dividend');
    expect(guessIncomeCategory('예금 이자'), 'interest');
    expect(guessIncomeCategory('주식 매도'), 'sale');
    expect(guessIncomeCategory('연말 성과급'), 'bonus');
    expect(guessIncomeCategory('회사'), 'salary');
    expect(categoryOf('dividend').group, IncomeGroup.invest);
    expect(categoryOf('salary').group, IncomeGroup.fixed);
    expect(expenseCategories.any((c) => c.isIncome), false);
  });
}
