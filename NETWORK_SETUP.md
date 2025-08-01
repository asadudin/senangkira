# Docker Network Setup for SenangKira

## External Network Configuration

The SenangKira Docker setup uses an external Docker network named `padux` for communication between containers and external services.

## Prerequisites

### Create External Network
Before starting the containers, create the external network:

```bash
# Create the padux network
docker network create padux

# Verify network creation
docker network ls | grep padux
```

### Network Benefits

**🔗 Container Communication:**
- All containers communicate using container names as hostnames
- No port mapping needed for internal communication
- External Nginx can access containers by name

**🛡️ Security:**
- Only exposed ports are accessible from host
- Internal services remain isolated
- External Nginx controls all public access

**⚡ Performance:**
- Direct container-to-container communication
- No port forwarding overhead
- Efficient network routing

## Service Communication

### Internal Hostnames
Within the `padux` network, services are accessible by container name:

- `senangkira_web:8000` - Django application
- `redis:6379` - Redis cache and message broker
- `senangkira_flower:5555` - Celery monitoring dashboard

### External Access
Only these services are accessible from outside:
- **None directly** - All traffic goes through external Nginx

### External Nginx Configuration
Your external Nginx should be in the same network or configured to access container names:

```nginx
upstream senangkira_backend {
    server senangkira_web:8000;
}

upstream senangkira_flower {
    server senangkira_flower:5555;
}
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        padux network                            │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ senangkira_web  │  │     redis       │  │senangkira_flower│ │
│  │     :8000       │◄─┤     :6379       ├─►│     :5555       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           ▲                                          ▲         │
│  ┌─────────────────┐  ┌─────────────────┐            │         │
│  │ celery_worker   │  │  celery_beat    │            │         │
│  │                 │  │                 │            │         │
│  └─────────────────┘  └─────────────────┘            │         │
└─────────────────────────────────────────────────────────────────┘
                       ▲                                ▲
              ┌─────────────────┐                      │
              │ External Nginx  │──────────────────────┘
              │ (in padux net)  │
              └─────────────────┘
                       ▲
               ┌─────────────────┐
               │  Public Access  │
               │ (Port 80/443)   │
               └─────────────────┘
```

## Setup Commands

### 1. Create Network
```bash
docker network create padux
```

### 2. Start Services
```bash
# Development
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up

# Production
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

### 3. Join External Nginx (if containerized)
```bash
# If your Nginx is also containerized, join it to the network
docker network connect padux nginx_container_name
```

### 4. Verify Network
```bash
# List containers in network
docker network inspect padux

# Test connectivity from external Nginx
docker exec nginx_container curl http://senangkira_web:8000/api/health/
```

## Troubleshooting

### Common Issues

**Network Not Found:**
```bash
ERROR: Network padux declared as external, but could not be found

# Solution: Create the network
docker network create padux
```

**Container Communication Failed:**
```bash
# Test from within network
docker run --rm --network padux alpine/curl curl http://senangkira_web:8000/api/health/

# Check network connectivity
docker network inspect padux
```

**External Nginx Can't Reach Containers:**
```bash
# If Nginx is containerized, connect it to the network
docker network connect padux nginx_container

# If Nginx is on host, ensure containers are accessible
# This depends on your Docker daemon configuration
```

### Network Cleanup
```bash
# Remove all containers first
docker-compose down

# Remove network (only if needed)
docker network rm padux

# Recreate network
docker network create padux
```

## Alternative: Bridge Network Access

If you need host-level access to services, you can expose specific ports:

```yaml
# In docker-compose.yaml, add ports only if needed from host
services:
  web:
    ports:
      - "8000:8000"  # Only if direct host access needed
  
  celery-flower:
    ports:
      - "5555:5555"  # Only if direct monitoring access needed
```

**Note:** This is not recommended if using external Nginx, as it creates unnecessary exposure.