import 'package:flutter_test/flutter_test.dart';
import 'package:pose_roulette/domain.dart';

void main() {
  test('wheel landing and travel are deterministic', () {
    expect(landingAngle(0,4), closeTo(wrapAngle(-3.141592653589793/4),1e-9));
    expect(spinTravel(0,landingAngle(2,5)), greaterThan(3.141592653589793*8));
  });
}
