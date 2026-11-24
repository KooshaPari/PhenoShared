//! ParetoRs — pure formatting helpers (no I/O).

/// Round to 2 decimal places.
pub fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

/// Round to 4 decimal places.
pub fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    const TOL_2: f64 = 0.001;
    const TOL_4: f64 = 0.00001;

    #[test]
    fn test_round2_basic() {
        assert!((round2(std::f64::consts::PI) - 314.0 / 100.0).abs() < TOL_2);
        assert_eq!(round2(1.234), 1.23);
        assert_eq!(round2(1.999), 2.00);
    }

    #[test]
    fn test_round2_zero() {
        assert_eq!(round2(0.0), 0.0);
    }

    #[test]
    fn test_round4_basic() {
        assert!((round4(std::f64::consts::PI) - std::f64::consts::PI).abs() < TOL_4);
        assert_eq!(round4(1.23456), 1.2346);
    }

    #[test]
    fn test_round4_zero() {
        assert_eq!(round4(0.0), 0.0);
    }
}
