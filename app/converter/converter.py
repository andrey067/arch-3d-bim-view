#!/usr/bin/env python3
"""
IFC to GLB Converter Service
Polls MinIO for new IFC files and converts them to GLB format.
"""

import os
import sys
import time
import logging
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from minio import Minio
import psycopg2
from psycopg2 import sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Environment variables
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'false').lower() == 'true'
MINIO_BUCKET_IFC = os.getenv('MINIO_BUCKET_IFC', 'ifc-files')
MINIO_BUCKET_GLB = os.getenv('MINIO_BUCKET_GLB', 'glb-files')
MINIO_BUCKET_THUMBNAILS = os.getenv('MINIO_BUCKET_THUMBNAILS', 'thumbnails')

POSTGRES_CONNECTION = os.getenv(
    'POSTGRES_CONNECTION',
    'Host=postgres;Port=5432;Database=arch3dar;Username=arch3dar;Password=arch3dar_secret'
)

# Conversion settings
POLL_INTERVAL = 10  # seconds
CONVERSION_TIMEOUT = 300  # seconds (5 minutes for large files)
IFCCONVERT_PATH = '/usr/local/bin/IfcConvert'


def parse_postgres_connection(conn_str: str) -> dict:
    """Parse PostgreSQL connection string into parameters."""
    params = {}
    for part in conn_str.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            # Normalize key names
            if key.lower() == 'host':
                params['host'] = value.strip()
            elif key.lower() == 'port':
                params['port'] = int(value.strip())
            elif key.lower() == 'database':
                params['database'] = value.strip()
            elif key.lower() in ('username', 'user'):
                params['user'] = value.strip()
            elif key.lower() == 'password':
                params['password'] = value.strip()
    return params


def get_minio_client() -> Minio:
    """Create and return MinIO client."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL
    )


def get_postgres_connection():
    """Create and return PostgreSQL connection."""
    params = parse_postgres_connection(POSTGRES_CONNECTION)
    return psycopg2.connect(**params)


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """Ensure the bucket exists, create if not."""
    if not client.bucket_exists(bucket_name):
        logger.info(f"Creating bucket: {bucket_name}")
        client.make_bucket(bucket_name)


def update_project_status(project_id: str, status: str, error_message: str = None) -> None:
    """Update project status in PostgreSQL database."""
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            if error_message:
                cur.execute(
                    """
                    UPDATE "Projects"
                    SET "Status" = %s, "ErrorMessage" = %s, "UpdatedAt" = %s
                    WHERE "Id" = %s
                    """,
                    (status, error_message, datetime.utcnow(), project_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE "Projects"
                    SET "Status" = %s, "UpdatedAt" = %s
                    WHERE "Id" = %s
                    """,
                    (status, datetime.utcnow(), project_id)
                )
            conn.commit()
            logger.info(f"Updated project {project_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update project status: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def get_queued_projects() -> list:
    """Get all projects with status 'Uploaded' or 'Queued'."""
    projects = []
    conn = None
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT "Id", "Name", "IfcObjectKey"
                FROM "Projects"
                WHERE "Status" IN ('Uploaded', 'Queued')
                ORDER BY "CreatedAt" ASC
                """
            )
            rows = cur.fetchall()
            for row in rows:
                projects.append({
                    'id': row[0],
                    'name': row[1],
                    'ifc_object_key': row[2]
                })
    except Exception as e:
        logger.error(f"Failed to fetch queued projects: {e}")
    finally:
        if conn:
            conn.close()
    return projects


def download_ifc_file(client: Minio, bucket: str, object_key: str, dest_path: str) -> bool:
    """Download IFC file from MinIO."""
    try:
        logger.info(f"Downloading {bucket}/{object_key} to {dest_path}")
        client.fget_object(bucket, object_key, dest_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download IFC file: {e}")
        return False


def upload_file_to_minio(client: Minio, bucket: str, object_key: str, file_path: str, content_type: str = None) -> bool:
    """Upload file to MinIO bucket."""
    try:
        logger.info(f"Uploading {file_path} to {bucket}/{object_key}")
        if content_type:
            client.fput_object(bucket, object_key, file_path, content_type=content_type)
        else:
            client.fput_object(bucket, object_key, file_path)
        return True
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return False


def run_ifcconvert(input_path: str, output_path: str, timeout: int = CONVERSION_TIMEOUT) -> bool:
    """Run IfcConvert to convert IFC to GLB."""
    try:
        logger.info(f"Running IfcConvert: {input_path} -> {output_path}")
        result = subprocess.run(
            [IFCCONVERT_PATH, input_path, output_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            logger.error(f"IfcConvert failed with exit code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return False
        logger.info("IfcConvert completed successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"IfcConvert timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"IfcConvert execution failed: {e}")
        return False


def generate_thumbnail(input_path: str, output_path: str, timeout: int = 120) -> bool:
    """Generate thumbnail using IfcConvert --thumbnail."""
    try:
        logger.info(f"Generating thumbnail: {input_path} -> {output_path}")
        result = subprocess.run(
            [IFCCONVERT_PATH, input_path, output_path, '--thumbnail'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            logger.warning(f"Thumbnail generation failed: {result.stderr}")
            return False
        logger.info("Thumbnail generated successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.warning(f"Thumbnail generation timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
        return False


def create_placeholder_thumbnail(output_path: str) -> bool:
    """Create a simple placeholder PNG thumbnail."""
    try:
        # Create a minimal valid PNG (1x1 transparent pixel)
        # PNG signature + IHDR + IDAT + IEND
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR length and type
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # bit depth, color type, etc.
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT length and type
            0x54, 0x08, 0x99, 0x63, 0x00, 0x00, 0x00, 0x02,  # compressed data
            0x00, 0x01, 0xE2, 0x21, 0xBC, 0x33, 0x00, 0x00,  # end of IDAT
            0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42,  # IEND
            0x60, 0x82
        ])
        with open(output_path, 'wb') as f:
            f.write(png_data)
        logger.info(f"Created placeholder thumbnail at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create placeholder thumbnail: {e}")
        return False


def process_project(project: dict, minio_client: Minio) -> bool:
    """Process a single project: download, convert, upload."""
    project_id = project['id']
    ifc_object_key = project['ifc_object_key']
    project_name = project.get('name', 'Unknown')

    logger.info(f"Processing project: {project_id} ({project_name})")

    # Create temp directory for this conversion
    temp_dir = tempfile.mkdtemp(prefix='ifc_converter_')
    ifc_path = os.path.join(temp_dir, 'input.ifc')
    glb_path = os.path.join(temp_dir, 'output.glb')
    thumbnail_path = os.path.join(temp_dir, 'thumbnail.png')

    try:
        # Update status to Processing
        update_project_status(project_id, 'Processing')

        # Step 1: Download IFC file
        if not download_ifc_file(minio_client, MINIO_BUCKET_IFC, ifc_object_key, ifc_path):
            raise Exception("Failed to download IFC file")

        # Verify IFC file exists and has content
        if not os.path.exists(ifc_path) or os.path.getsize(ifc_path) == 0:
            raise Exception("Downloaded IFC file is empty or missing")

        # Step 2: Convert IFC to GLB
        if not run_ifcconvert(ifc_path, glb_path):
            raise Exception("IfcConvert failed to convert IFC to GLB")

        # Verify GLB was created
        if not os.path.exists(glb_path) or os.path.getsize(glb_path) == 0:
            raise Exception("GLB file was not created by IfcConvert")

        # Step 3: Upload GLB to MinIO
        glb_object_key = f"projects/{project_id}/model.glb"
        if not upload_file_to_minio(minio_client, MINIO_BUCKET_GLB, glb_object_key, glb_path, 'model/gltf-binary'):
            raise Exception("Failed to upload GLB to MinIO")

        # Step 4: Generate thumbnail
        thumbnail_success = generate_thumbnail(ifc_path, thumbnail_path)
        if not thumbnail_success:
            # Create placeholder if thumbnail generation fails
            logger.warning("Creating placeholder thumbnail")
            create_placeholder_thumbnail(thumbnail_path)

        # Step 5: Upload thumbnail
        thumbnail_object_key = f"projects/{project_id}/thumbnail.png"
        if not upload_file_to_minio(minio_client, MINIO_BUCKET_THUMBNAILS, thumbnail_object_key, thumbnail_path, 'image/png'):
            logger.warning("Failed to upload thumbnail, but continuing")

        # Step 6: Update database with results
        update_project_status(project_id, 'Completed')

        # Clean up GLB path before updating DB with keys
        conn = get_postgres_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE "Projects"
                    SET "GlbObjectKey" = %s, "ThumbnailObjectKey" = %s, "Status" = %s, "UpdatedAt" = %s
                    WHERE "Id" = %s
                    """,
                    (glb_object_key, thumbnail_object_key, 'Completed', datetime.utcnow(), project_id)
                )
                conn.commit()
        finally:
            conn.close()

        logger.info(f"Project {project_id} completed successfully")
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Project {project_id} failed: {error_msg}")
        update_project_status(project_id, 'Failed', error_msg)
        return False

    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")


def poll_and_process():
    """Main polling loop."""
    logger.info("Starting IFC to GLB converter service")
    logger.info(f"MinIO endpoint: {MINIO_ENDPOINT}")
    logger.info(f"IFC bucket: {MINIO_BUCKET_IFC}")
    logger.info(f"GLB bucket: {MINIO_BUCKET_GLB}")
    logger.info(f"Thumbnails bucket: {MINIO_BUCKET_THUMBNAILS}")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")

    # Initialize MinIO client
    minio_client = get_minio_client()

    # Ensure buckets exist
    try:
        ensure_bucket_exists(minio_client, MINIO_BUCKET_IFC)
        ensure_bucket_exists(minio_client, MINIO_BUCKET_GLB)
        ensure_bucket_exists(minio_client, MINIO_BUCKET_THUMBNAILS)
    except Exception as e:
        logger.warning(f"Could not verify buckets (may not be available yet): {e}")

    # Verify IfcConvert is available
    if not os.path.exists(IFCCONVERT_PATH):
        logger.error(f"IfcConvert not found at {IFCCONVERT_PATH}")
        logger.error("Please install IfcOpenShell IfcConvert")
        sys.exit(1)

    logger.info("Converter service initialized successfully")

    # Main polling loop
    while True:
        try:
            projects = get_queued_projects()
            if projects:
                logger.info(f"Found {len(projects)} project(s) to process")
                for project in projects:
                    process_project(project, minio_client)
            else:
                logger.debug("No projects to process")
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    try:
        poll_and_process()
    except KeyboardInterrupt:
        logger.info("Converter service shutting down")
        sys.exit(0)