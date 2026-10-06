class NumberGroup {
  final List<int> numbers;
  final int count;

  const NumberGroup({required this.numbers, this.count = 0});

  factory NumberGroup.fromJson(Map<String, dynamic> json, String key) {
    final values =
        json[key] ?? json['numbers'] ?? json['combination'] ?? const [];
    return NumberGroup(
      numbers: _numbers(values),
      count: _int(json['count']),
    );
  }

  static List<int> _numbers(dynamic value) => value is List
      ? value.whereType<num>().map((item) => item.toInt()).toList()
      : const [];

  static int _int(dynamic value) => value is num ? value.toInt() : 0;
}

class Prediction {
  final List<int> f1;
  final List<int> f2;
  final List<int> f3;
  final List<int> special;

  const Prediction({
    this.f1 = const [],
    this.f2 = const [],
    this.f3 = const [],
    this.special = const [],
  });

  factory Prediction.fromJson(Map<String, dynamic> json) => Prediction(
        f1: _numbers(json['f1_prediction'] ?? json['f1']),
        f2: _numbers(json['f2_prediction'] ?? json['f2']),
        f3: _numbers(json['f3_prediction'] ?? json['f3']),
        special: _numbers(json['special_prediction'] ?? json['special']),
      );

  static List<int> _numbers(dynamic value) => value is List
      ? value.whereType<num>().map((item) => item.toInt()).toList()
      : const [];
}
