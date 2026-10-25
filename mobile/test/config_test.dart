import 'package:dermedics_ai/core/config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('server address is normalised', () {
    expect(AppConfig.normalize('192.168.18.128:8000'), 'http://192.168.18.128:8000');
    expect(AppConfig.normalize(' http://192.168.18.128:8000/api/ '), 'http://192.168.18.128:8000');
    expect(AppConfig.normalize('https://dermedics.example.com/'), 'https://dermedics.example.com');
    expect(AppConfig.normalize('   '), isNull);
    expect(AppConfig.normalize(null), isNull);
  });
}
