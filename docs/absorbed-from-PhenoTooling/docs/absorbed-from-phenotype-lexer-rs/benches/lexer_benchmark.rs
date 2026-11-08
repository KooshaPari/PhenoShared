use criterion::{black_box, criterion_group, criterion_main, Criterion};
use netscript::Lexer;

fn bench_lexer_tokenize(c: &mut Criterion) {
    let input = "let x = 42;\nlet y = \"hello\";\nif x > 0 { return x + y; }\n";
    c.bench_function("lexer_tokenize", |b| {
        b.iter(|| {
            let mut lexer = Lexer::new(black_box(input));
            lexer.tokenize()
        })
    });
}

fn bench_lexer_tokenize_complex(c: &mut Criterion) {
    let input = r#"
        fn add(a, b) {
            let result = a + b;
            return result;
        }
        let sum = add(10, 20);
        print(sum);
        while sum < 100 {
            sum = sum + 1;
        }
        if sum == 100 {
            print("done");
        } else {
            print("not done");
        }
    "#;
    c.bench_function("lexer_tokenize_complex", |b| {
        b.iter(|| {
            let mut lexer = Lexer::new(black_box(input));
            lexer.tokenize()
        })
    });
}

criterion_group!(benches, bench_lexer_tokenize, bench_lexer_tokenize_complex);
criterion_main!(benches);
