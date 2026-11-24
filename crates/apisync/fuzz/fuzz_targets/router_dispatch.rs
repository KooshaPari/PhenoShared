#![no_main]

use libfuzzer_sys::fuzz_target;

use apisync::domain::{CreateItem, Endpoint, Request};
use apisync::endpoints::ItemCrudEndpoint;

/// Smoke-test the router dispatch path with arbitrary method/path/body bytes.
///
/// This target is intentionally minimal — it just exercises `Endpoint::handle`
/// against the `ItemCrudEndpoint` to make sure random input never panics
/// (audit finding L11/L25). Anything more interesting belongs as a unit test
/// with deterministic inputs.
fuzz_target!(|data: &[u8]| {
    let method = match data.first().copied().unwrap_or(0) % 4 {
        0 => "GET",
        1 => "POST",
        2 => "PUT",
        _ => "DELETE",
    };
    let path = format!("/items/{}", data.len());
    let mut req = Request::new(path, method);
    if data.len() > 1 {
        req.body = Some(data.to_vec());
    }

    // Try to decode a CreateItem from arbitrary bytes. We don't care about
    // success — we only care that the endpoint never panics on weird input.
    if method == "POST" {
        let _ = serde_json::from_slice::<CreateItem>(data);
    }

    let endpoint = ItemCrudEndpoint::new();
    let _ = futures::executor::block_on(endpoint.handle(req));
});
