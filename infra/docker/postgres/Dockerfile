FROM postgres:16-alpine

# Create database and dedicated role
ENV POSTGRES_DB=app3d
ENV POSTGRES_USER=app3d
ENV POSTGRES_PASSWORD=app3d

# Init scripts run automatically on first start
COPY init.sh /docker-entrypoint-initdb.d/01-init.sh
RUN chmod +x /docker-entrypoint-initdb.d/01-init.sh

EXPOSE 5432
