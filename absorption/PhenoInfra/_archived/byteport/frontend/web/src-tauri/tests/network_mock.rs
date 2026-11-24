#[path = "../src/network.rs"]
mod network;

use network::{
    delete_object_command, fetch_metadata_command, list_objects_command, upload_chunk_command,
    MockNetworkClient, NetworkError, ObjectMetadata, ObjectSummary,
};

#[test]
fn upload_chunk_command_passes_expected_bytes() {
    let expected = vec![1_u8, 2, 3, 4];
    let mut client = MockNetworkClient::new();

    client
        .expect_upload_chunk()
        .once()
        .withf({
            let expected = expected.clone();
            move |key, bytes| key == "chunks/demo.bin" && bytes == expected.as_slice()
        })
        .return_once(|_, _| Ok(()));

    let result = upload_chunk_command(&client, "chunks/demo.bin", expected);

    assert!(result.is_ok());
    client.checkpoint();
}

#[test]
fn upload_chunk_command_maps_network_errors() {
    let mut client = MockNetworkClient::new();

    client
        .expect_upload_chunk()
        .once()
        .withf(|key, bytes| key == "chunks/demo.bin" && bytes == [9_u8, 9, 9].as_slice())
        .return_once(|_, _| Err(NetworkError::new("upload failed")));

    let result = upload_chunk_command(&client, "chunks/demo.bin", vec![9_u8, 9, 9]);

    assert_eq!(result, Err(String::from("upload failed")));
    client.checkpoint();
}

#[test]
fn metadata_delete_and_list_commands_delegate_to_client() {
    let mut client = MockNetworkClient::new();

    client
        .expect_fetch_metadata()
        .once()
        .withf(|key| key == "objects/demo.bin")
        .return_once(|_| {
            Ok(ObjectMetadata {
                key: String::from("objects/demo.bin"),
                size: 42,
            })
        });

    client
        .expect_delete_object()
        .once()
        .withf(|key| key == "objects/demo.bin")
        .return_once(|_| Ok(()));

    client
        .expect_list_objects()
        .once()
        .withf(|prefix| prefix == "objects/")
        .return_once(|_| {
            Ok(vec![ObjectSummary {
                key: String::from("objects/demo.bin"),
            }])
        });

    let metadata = fetch_metadata_command(&client, "objects/demo.bin").unwrap();
    let delete_result = delete_object_command(&client, "objects/demo.bin");
    let objects = list_objects_command(&client, "objects/").unwrap();

    assert_eq!(
        metadata,
        ObjectMetadata {
            key: String::from("objects/demo.bin"),
            size: 42,
        }
    );
    assert!(delete_result.is_ok());
    assert_eq!(
        objects,
        vec![ObjectSummary {
            key: String::from("objects/demo.bin"),
        }]
    );
    client.checkpoint();
}
