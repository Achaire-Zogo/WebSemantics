# Dockerfile
FROM openjdk:11-jre-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    python3 \
    python3-pip \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set up Jena Fuseki
WORKDIR /opt
RUN wget https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-4.10.0.tar.gz \
    && tar -xzf apache-jena-fuseki-4.10.0.tar.gz \
    && mv apache-jena-fuseki-4.10.0 fuseki \
    && rm apache-jena-fuseki-4.10.0.tar.gz

# Create directories
RUN mkdir -p /app/data/images \
    && mkdir -p /app/data/ontology \
    && mkdir -p /app/service \
    && mkdir -p /var/fuseki

# Copy application files
COPY . /app/

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

# Set up Fuseki configuration
COPY fuseki-config.ttl /var/fuseki/config.ttl

# Expose ports
EXPOSE 3030 8080 9200

# Copy startup script
COPY start-services.sh /app/
RUN chmod +x /app/start-services.sh

CMD ["/app/start-services.sh"]