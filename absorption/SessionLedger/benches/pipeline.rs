use std::{hint::black_box, time::Duration};

use criterion::{criterion_group, criterion_main, Criterion, Throughput};
use session_ledger::domain::session::{Corpus, Message, Role, Session};

fn representative_session() -> Session {
    let mut session = Session::new("bench-session", Corpus::Forge);
    session.cwd = Some("/workspace/session-ledger".into());
    session.title = Some("Benchmark the continuation pipeline".into());

    for index in 0..100 {
        session.messages.push(Message::new(
            Role::User,
            format!(
                "Iteration {index}: update src/distill/compiler.rs, preserve the public API, and run cargo test"
            ),
        ));
        session.messages.push(Message::new(
            Role::Assistant,
            format!("Iteration {index}: updated the compiler and verified the requested behavior"),
        ));
    }

    session
}

fn pipeline_benches(c: &mut Criterion) {
    let session = representative_session();
    let bundle = session_ledger::distill::compile(&session);

    let mut group = c.benchmark_group("pipeline");
    group.throughput(Throughput::Elements(session.messages.len() as u64));

    group.bench_function("distill_compile_200_messages", |b| {
        b.iter(|| session_ledger::distill::compile(black_box(&session)));
    });
    group.bench_function("okf_export_200_messages", |b| {
        b.iter(|| {
            session_ledger::export_to_okf(black_box(&bundle), black_box(session.corpus.as_str()))
        });
    });
    group.bench_function("inject_render_200_messages", |b| {
        b.iter(|| {
            session_ledger::render_prompt(black_box(&bundle))
                .expect("compiled bundle should remain injectable")
        });
    });

    group.finish();
}

fn configured_criterion() -> Criterion {
    let mut criterion = Criterion::default().configure_from_args();

    if let Ok(sample_size) = std::env::var("SESSION_LEDGER_BENCH_SAMPLE_SIZE") {
        let sample_size = sample_size
            .parse::<usize>()
            .expect("SESSION_LEDGER_BENCH_SAMPLE_SIZE must be an integer");
        criterion = criterion.sample_size(sample_size);
    }
    if let Ok(seconds) = std::env::var("SESSION_LEDGER_BENCH_WARM_UP_SECONDS") {
        let seconds =
            seconds.parse::<f64>().expect("SESSION_LEDGER_BENCH_WARM_UP_SECONDS must be a number");
        criterion = criterion.warm_up_time(Duration::from_secs_f64(seconds));
    }
    if let Ok(seconds) = std::env::var("SESSION_LEDGER_BENCH_MEASUREMENT_SECONDS") {
        let seconds = seconds
            .parse::<f64>()
            .expect("SESSION_LEDGER_BENCH_MEASUREMENT_SECONDS must be a number");
        criterion = criterion.measurement_time(Duration::from_secs_f64(seconds));
    }

    criterion
}

criterion_group! {
    name = benches;
    config = configured_criterion();
    targets = pipeline_benches
}
criterion_main!(benches);
