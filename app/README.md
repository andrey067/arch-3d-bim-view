# Arch3DAR — BIM 3D Viewer

A lightweight, browser-first platform for sharing BIM models. Upload an IFC file, get a shareable link that renders the full 3D model with element-level property inspection and optional AR viewing.

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd arch3dar

# Start all services
docker compose up -d

# Access the application
# Frontend: http://localhost
# MinIO Console: http://localhost:9001
# Backend API: http://localhost/api
```

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4 GB RAM minimum (8 GB recommended for large IFC files)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   nginx     │────▶│   frontend  │     │   postgres  │
│   :80/:443  │     │   :3000     │     │   :5432     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        ▲
       ▼                                        │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   backend   │────▶│    minio    │     │  converter  │
│   :5000     │     │   :9000     │     │   (worker)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Services

| Service    | Description                          | Port  |
|------------|--------------------------------------|-------|
| nginx      | Reverse proxy, SSL termination       | 80, 443 |
| frontend   | React + Vite BIM viewer              | 3000  |
| backend    | ASP.NET Core 9 API                   | 5000  |
| postgres   | PostgreSQL database                  | 5432  |
| minio      | S3-compatible object storage         | 9000, 9001 |
| converter  | IFC-to-GLB conversion (IfcConvert)   | —     |

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# PostgreSQL
POSTGRES_USER=arch3dar
POSTGRES_PASSWORD=arch3dar_secret
POSTGRES_DB=arch3dar

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET_IFC=ifc-files
MINIO_BUCKET_GLB=glb-files
MINIO_BUCKET_THUMBNAILS=thumbnails
```

## Usage

### Upload an IFC File

1. Open `http://localhost` in your browser
2. Click "Upload New"
3. Drag and drop your `.ifc` file or click to browse
4. Enter a project name
5. Click "Upload"

### View a BIM Model

1. Go to the Projects page
2. Click "View" on any project
3. Use mouse to orbit, pan, and zoom
4. Click elements to see their properties
5. Use the spatial tree to navigate the model

### View in AR

1. Open the share link on a mobile device
2. Click "View in AR"
3. Point your camera at a flat surface
4. The model will appear in augmented reality

## API Endpoints

| Method | Endpoint              | Description                    |
|--------|-----------------------|--------------------------------|
| POST   | /api/projects/upload  | Upload IFC file                |
| GET    | /api/projects         | List all projects              |
| GET    | /api/projects/{id}    | Get project details            |
| GET    | /api/share/{id}       | Get share data (public)        |
| GET    | /health               | Health check                   |

## MinIO Buckets

| Bucket      | Contents              |
|-------------|-----------------------|
| ifc-files   | Original IFC uploads  |
| glb-files   | Converted GLB models  |
| thumbnails  | Project thumbnails    |

## Development

### Frontend

```bash
cd app/frontend
npm install
npm run dev
# Access at http://localhost:5173
```

### Backend

```bash
cd app/backend
dotnet restore
dotnet run
# Access at http://localhost:5000
```

### Converter

```bash
cd app/converter
pip install -r requirements.txt
python3 converter.py
```

## Deployment

### Production

1. Update `.env` with production credentials
2. Configure SSL certificates in `nginx/nginx.conf`
3. Update `docker-compose.yml` with your domain
4. Run `docker compose -f docker-compose.yml up -d`

### SSL Configuration

1. Obtain SSL certificates (e.g., Let's Encrypt)
2. Place certificates in `nginx/certs/`
3. Uncomment SSL section in `nginx/nginx.conf`
4. Restart nginx: `docker compose restart nginx`

## Troubleshooting

### Converter not processing files

```bash
# Check converter logs
docker compose logs converter

# Verify IfcConvert is installed
docker compose exec converter IfcConvert --version
```

### Upload fails with 413

The nginx `client_max_body_size` is set to 500MB. For larger files, update `nginx/nginx.conf`.

### Database connection issues

```bash
# Check postgres is healthy
docker compose ps postgres

# View postgres logs
docker compose logs postgres
```

## License

Proprietary — Internal use only.
