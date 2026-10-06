import 'package:flutter/foundation.dart';

class LotteryResult {
  final DateTime drawDate;
  final String drawNumber;
  final String lotteryType;
  final List<int> winningNumbers;
  final int? specialNumber;

  const LotteryResult({
    required this.drawDate,
    required this.drawNumber,
    required this.lotteryType,
    required this.winningNumbers,
    this.specialNumber,
  });

  factory LotteryResult.fromJson(Map<String, dynamic> json) {
    final rawDate = json['draw_datetime'] ??
        json['draw_date'] ??
        json['date'] ??
        json['drawDate'];
    final rawNumbers =
        json['winning_numbers'] ?? json['numbers'] ?? json['winningNumbers'];
    if (rawDate == null) {
      throw const FormatException('Thiếu ngày quay thưởng');
    }
    if (rawNumbers is! List) {
      throw const FormatException('Thiếu bộ số trúng thưởng');
    }
    final date = rawDate is DateTime
        ? rawDate
        : rawDate is num
            ? DateTime.fromMillisecondsSinceEpoch(rawDate.toInt())
            : DateTime.tryParse(rawDate.toString());
    if (date == null) throw const FormatException('Ngày quay không hợp lệ');
    debugPrint(
      '[PARSE] draw ${json['draw_number'] ?? '<unknown>'} '
      'datetime=$rawDate numbers=${rawNumbers.length}',
    );
    return LotteryResult(
      drawDate: date,
      drawNumber: (json['draw_number'] ?? json['id'] ?? '').toString(),
      lotteryType: (json['lottery_type'] ?? json['game_type'] ?? '').toString(),
      winningNumbers:
          rawNumbers.whereType<num>().map((number) => number.toInt()).toList(),
      specialNumber: json['special_number'] is num
          ? (json['special_number'] as num).toInt()
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'draw_date': drawDate.toIso8601String(),
        'draw_number': drawNumber,
        'lottery_type': lotteryType,
        'winning_numbers': winningNumbers,
        'special_number': specialNumber,
      };
}
