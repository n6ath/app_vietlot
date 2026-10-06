import 'package:flutter_test/flutter_test.dart';
import 'package:vietlott_ai/models/lottery_result.dart';
import 'package:vietlott_ai/models/lottery_statistics.dart';

void main() {
  test('phân tích kết quả chịu được kiểu số hỗn hợp', () {
    final result = LotteryResult.fromJson({
      'draw_date': '2026-09-23T12:00:00Z',
      'draw_number': 123,
      'winning_numbers': [1, 2.0, 'bỏ qua'],
    });
    expect(result.drawNumber, '123');
    expect(result.winningNumbers, [1, 2]);
  });

  test('phân tích thống kê bỏ qua trường không hợp lệ', () {
    final stats = LotteryStatistics.fromJson({
      'number_frequency': {'1': 4, 'x': 'sai'},
      'hot_numbers': [1, 'sai', 7.0],
      'overdue_numbers': [9],
    });
    expect(stats.numberFrequency, {1: 4});
    expect(stats.hotNumbers, [1, 7]);
    expect(stats.overdueNumbers, [9]);
  });
}
