//! Property-based tests for domain models using proptest

use std::sync::Arc;
use std::thread;

use apisync::domain::{CreateItem, ItemStore, UpdateItem};
use proptest::prelude::*;

proptest! {
    /// Property 1: Item creation with random data preserves all fields
    /// and assigns monotonically increasing IDs.
    #[test]
    fn prop_item_creation_with_random_data(
        name in any::<String>(),
        description in any::<String>(),
    ) {
        let store = ItemStore::new();
        let create = CreateItem {
            name: name.clone(),
            description: description.clone(),
        };
        let item = store.create(create);

        assert_eq!(item.name, name);
        assert_eq!(item.description, description);
        assert_eq!(item.id, 1);

        // Second creation should get the next ID
        let item2 = store.create(CreateItem {
            name: "second".to_string(),
            description: "desc".to_string(),
        });
        assert_eq!(item2.id, 2);
    }

    /// Property 2: ItemStore round-trip
    /// create -> get -> update -> get -> delete -> get(none)
    #[test]
    fn prop_item_store_roundtrip(
        name in any::<String>(),
        description in any::<String>(),
        new_name in any::<String>(),
        new_description in any::<String>(),
    ) {
        let store = ItemStore::new();

        // Create
        let create = CreateItem { name, description };
        let item = store.create(create);
        let id = item.id;

        // Get should return the exact item
        let got = store.get(id).unwrap();
        assert_eq!(got, item);

        // Update both fields
        let update = UpdateItem {
            name: Some(new_name.clone()),
            description: Some(new_description.clone()),
        };
        let updated = store.update(id, update).unwrap();
        assert_eq!(updated.name, new_name);
        assert_eq!(updated.description, new_description);
        assert_eq!(updated.id, id);

        // Get after update should reflect changes
        let got_after_update = store.get(id).unwrap();
        assert_eq!(got_after_update, updated);

        // Delete should return the last known item
        let deleted = store.delete(id).unwrap();
        assert_eq!(deleted, got_after_update);

        // Get after delete should be None
        assert!(store.get(id).is_none());
    }

    /// Property 2b: ItemStore round-trip with partial update
    /// (update only name, leaving description unchanged)
    #[test]
    fn prop_item_store_partial_update_roundtrip(
        name in any::<String>(),
        description in any::<String>(),
        new_name in any::<String>(),
    ) {
        let store = ItemStore::new();
        let create = CreateItem { name, description: description.clone() };
        let item = store.create(create);
        let id = item.id;

        // Update only name
        let update = UpdateItem {
            name: Some(new_name.clone()),
            description: None,
        };
        let updated = store.update(id, update).unwrap();
        assert_eq!(updated.name, new_name);
        assert_eq!(updated.description, description);

        // Get after partial update
        let got = store.get(id).unwrap();
        assert_eq!(got, updated);

        // Delete and verify gone
        store.delete(id);
        assert!(store.get(id).is_none());
    }

    /// Property 3: Idempotency of list operations
    /// Calling list() multiple times without mutations yields identical results.
    #[test]
    fn prop_list_idempotency(
        items in prop::collection::vec(
            (any::<String>(), any::<String>()),
            0..20,
        ),
    ) {
        let store = ItemStore::new();
        for (name, description) in &items {
            store.create(CreateItem {
                name: name.clone(),
                description: description.clone(),
            });
        }

        let list1 = store.list();
        let list2 = store.list();
        let list3 = store.list();

        assert_eq!(list1, list2);
        assert_eq!(list2, list3);

        // Verify list length matches number of created items
        assert_eq!(list1.len(), items.len());
    }

    /// Property 3b: List ordering is stable (sorted by id)
    #[test]
    fn prop_list_sorted_by_id(
        items in prop::collection::vec(
            (any::<String>(), any::<String>()),
            1..15,
        ),
    ) {
        let store = ItemStore::new();
        for (name, description) in &items {
            store.create(CreateItem {
                name: name.clone(),
                description: description.clone(),
            });
        }

        let list = store.list();
        for i in 1..list.len() {
            assert!(list[i - 1].id < list[i].id, "list should be sorted by id ascending");
        }
    }

    /// Property 5: Update on non-existent item returns None
    #[test]
    fn prop_update_nonexistent_returns_none(
        id in any::<u64>(),
        new_name in any::<String>(),
        new_description in any::<String>(),
    ) {
        let store = ItemStore::new();
        let update = UpdateItem {
            name: Some(new_name),
            description: Some(new_description),
        };
        assert!(store.update(id, update).is_none());
    }

    /// Property 6: Delete on non-existent item returns None
    #[test]
    fn prop_delete_nonexistent_returns_none(
        id in any::<u64>(),
    ) {
        let store = ItemStore::new();
        assert!(store.delete(id).is_none());
    }

    /// Property 7: Get on non-existent item returns None
    #[test]
    fn prop_get_nonexistent_returns_none(
        id in any::<u64>(),
    ) {
        let store = ItemStore::new();
        assert!(store.get(id).is_none());
    }

    /// Property 8: Idempotency of delete
    /// Deleting the same item twice is equivalent to deleting once.
    #[test]
    fn prop_delete_idempotent(
        name in any::<String>(),
        description in any::<String>(),
    ) {
        let store = ItemStore::new();
        let item = store.create(CreateItem { name, description });
        let id = item.id;

        // First delete succeeds
        assert!(store.delete(id).is_some());
        // Second delete returns None
        assert!(store.delete(id).is_none());
        // Store is empty
        assert!(store.list().is_empty());
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(50))]

    /// Property 4: Concurrent access safety
    /// Multiple threads performing create/get/update/delete should not panic,
    /// deadlock, or corrupt the store.
    #[test]
    fn prop_concurrent_access_safety(
        ops_per_thread in 1usize..30usize,
        num_threads in 2usize..8usize,
    ) {
        let store = Arc::new(ItemStore::new());
        let mut handles = vec![];

        for t in 0..num_threads {
            let store_clone = Arc::clone(&store);
            let handle = thread::spawn(move || {
                for i in 0..ops_per_thread {
                    let name = format!("thread-{t}-op-{i}");
                    let description = format!("desc-{t}-{i}");

                    // Create
                    let item = store_clone.create(CreateItem {
                        name,
                        description,
                    });

                    // Get
                    let got = store_clone.get(item.id);
                    assert!(got.is_some(), "get should succeed immediately after create");

                    // Update
                    let updated = store_clone.update(
                        item.id,
                        UpdateItem {
                            name: Some(format!("updated-{t}-{i}")),
                            description: Some(format!("updated-desc-{t}-{i}")),
                        },
                    );
                    assert!(updated.is_some(), "update should succeed on existing item");

                    // Delete
                    let deleted = store_clone.delete(item.id);
                    assert!(deleted.is_some(), "delete should succeed on existing item");

                    // Verify gone
                    assert!(store_clone.get(item.id).is_none(), "item should be gone after delete");
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().expect("thread should not panic");
        }

        // After all threads complete and delete everything, store should be empty
        let remaining = store.list();
        assert!(remaining.is_empty(), "store should be empty after all concurrent deletes");
    }

    /// Property 4b: Concurrent read-only access is safe
    /// Multiple threads only calling list() and get() should not panic.
    #[test]
    fn prop_concurrent_read_only_access(
        seed_items in prop::collection::vec(
            (any::<String>(), any::<String>()),
            1..10,
        ),
        num_threads in 2usize..8usize,
    ) {
        let store = Arc::new(ItemStore::new());
        for (name, description) in &seed_items {
            store.create(CreateItem {
                name: name.clone(),
                description: description.clone(),
            });
        }

        let seed_count = seed_items.len();
        let mut handles = vec![];
        for _ in 0..num_threads {
            let store_clone = Arc::clone(&store);
            let handle = thread::spawn(move || {
                for _ in 0..100 {
                    let list = store_clone.list();
                    assert_eq!(list.len(), seed_count);
                    for item in &list {
                        let got = store_clone.get(item.id);
                        assert!(got.is_some(), "get should find item that exists in list");
                    }
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().expect("read-only thread should not panic");
        }
    }
}
