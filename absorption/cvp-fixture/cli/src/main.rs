use pipeline::{Pipeline, Item};
use pipeline::filters::{PredicateFilter, MapFilter, TakeFilter};

fn main() {
    let items: Vec<Item> = vec![
        Item::new("user:1", "Alice"),
        Item::new("user:2", "Bob"),
        Item::new("user:3", "Charlie"),
        Item::new("user:4", "Diana"),
    ];

    let result = Pipeline::new(items)
        .apply(&TakeFilter::new(3))
        .apply(&MapFilter::new(|mut i| {
            i.tags.push("processed".into());
            i
        }))
        .apply(&PredicateFilter::new(|i| i.key != "user:3"))
        .into_items();

    for item in &result {
        println!("{item}");
    }

    println!("Total: {} items", result.len());
}
