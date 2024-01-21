import os
import psycopg2
from azure.storage.blob import BlobServiceClient
# Replace with your connection string and container name
connection_string = os.environ.get("AZ_BLOB_CONNECTION", None)
container_name = os.environ.get("AZ_BLOB_CONTAINER", None)

pgParams = {
    'database': os.getenv('PG_DATABASE'),
    'user': os.getenv('PG_USER'),
    'password': os.getenv('PG_PASS'),
    'host': os.getenv('PG_HOST'),
    'port': 5432
}

conn = psycopg2.connect(**pgParams)
cur = conn.cursor()

def download_all_files_from_blob():
    # Create a BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # Access the container
    container_client = blob_service_client.get_container_client(container_name)

    # List all blobs in the container and download them
    for blob in container_client.list_blobs():
        blob_client = container_client.get_blob_client(blob)
        file_path = os.path.join("download/", blob.name)  # Define your local directory path
        file_id, _ = os.path.splitext(blob.name)

        # check if the file expected to be processed
        cur.execute("select id from movies m where m.processed = FALSE and m.\"gDriveId\" = %s",
                    (file_id,))
        rows = cur.fetchall()

        if not rows:
            continue  # Break the loop if no more rows are returned

        with open(file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
            print(f"File saved: {file_path}")