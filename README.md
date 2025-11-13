# 🚀 GCP Microservices Playground

**Production-ready microservices platform on Google Cloud Platform**

[![Status](https://img.shields.io/badge/status-production--ready-success)]()
[![Cost](https://img.shields.io/badge/cost-~$2--3%2Fmonth-blue)]()
[![Build Time](https://img.shields.io/badge/build-5--10s-green)]()

## ✨ Features

- ⚡ **Ultra-Fast Builds**: 5-10 seconds (vs 2-3 minutes)
- 💰 **Minimal Cost**: ~$2-3/month idle, auto-scales to zero
- 🔍 **Complete Tracing**: Every operation tracked with `run_id`
- 🛠️ **Multi-Language**: Python, Node.js, Go support
- 🚀 **CI/CD Ready**: Automated builds with Google Cloud Build
- 📦 **Easy Deployment**: One command to deploy any service
- 🔄 **Rollback Support**: Instant rollback to any version
- 📊 **Full Observability**: Monitoring, logging, tracing built-in

## 🎯 What's Included

All **9 major components** complete and ready to use:

1. ✅ **Deployment System** - Pure Python using Google Cloud APIs
2. ✅ **Shared SDK** - Complete library for microservices
3. ✅ **Terraform Infrastructure** - Production-ready GCP setup
4. ✅ **Base Docker Images** - Python, Node.js, Go
5. ✅ **CI/CD System** - Automated Cloud Build triggers
6. ✅ **API Gateway** - Service discovery and routing
7. ✅ **Service Templates** - Quick-start for new services
8. ✅ **Developer Tools** - CLI for creating and deploying
9. ✅ **Complete Documentation** - Step-by-step guides

## 🏗️ Architecture

```
Client → API Gateway → Microservices → Infrastructure
                ↓          ↓              ↓
          run_id tracking across all components
```

- **API Gateway**: Auto service discovery, run_id injection
- **Microservices**: Cloud Run, scale to zero, auto-healing
- **Tracing**: OpenTelemetry + Cloud Trace
- **Versioning**: Git SHA-based, automatic

## 🚀 Quick Start (30 minutes)

### 1. Deploy Infrastructure

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy GCP infrastructure
cd infrastructure/terraform
terraform apply

# Build base images (one-time, 10-15 min)
cd ../../base-images
.\build-all.ps1  # Windows
./build-all.sh   # Linux/Mac

# Set up CI/CD
cd ..
python -m cicd.cli setup

# Deploy API Gateway
python -m deploy.cli deploy api-gateway
```

### 2. Create Your First Service

```bash
# Create from template (2 minutes)
python tools/create_service.py my-service --lang python

# Deploy
python -m deploy.cli deploy my-service

# Verify
curl https://api-gateway-xxx.run.app/services
```

### 3. Start Building!

Your platform is ready. Create more services, deploy, and scale! 🎉

## 📖 Documentation

- **[Quick Start](QUICKSTART.md)** - Get started in 5 minutes
- **[Complete Setup Guide](docs/SETUP_GUIDE.md)** - Detailed 30-minute setup
- **[Complete Guide](docs/COMPLETE_GUIDE.md)** - Full platform documentation
- **[Command Reference](COMMAND_REFERENCE.md)** - All commands in one place
- **[Final Summary](FINAL_SUMMARY.md)** - What's been built

## 📁 Project Structure

```
gcp-graphql/
├── base-images/           # Pre-built Docker images (Python, Node.js, Go)
├── cicd/                  # CI/CD trigger management
├── core-services/         # Infrastructure services
│   └── api-gateway/       # GraphQL Federation Gateway
├── deploy/                # Deployment system (6 modules)
├── docs/                  # Complete documentation
├── infrastructure/        # Terraform IaC
├── services/              # ⭐ Your microservices go here
├── shared/
│   └── python/
│       └── playground_sdk # SDK for microservices
├── tools/
│   ├── create_service.py  # Service generator
│   └── templates/         # Service templates
└── config.json            # GCP configuration
```

## 💻 Usage Examples

### Create and Deploy a Service

```bash
# Create from template
python tools/create_service.py payment-service --lang python

# Edit your business logic
vim services/payment-service/src/handlers.py

# Deploy to Cloud Run
python -m deploy.cli deploy payment-service
```

### Write a Handler

```python
from playground_sdk import handler, RunContext, router

@handler
async def process_payment(run: RunContext, amount: float):
    """Process payment - automatically tracked with run.run_id"""

    # Call other services
    order = await router.call_service('db-service', '''
        mutation {
            insert(table: "orders", data: {amount: $amount}) {
                id
            }
        }
    ''', {'amount': amount})

    return {"success": True, "order_id": order['id']}
```

### Deploy Multiple Services

```bash
# Parallel deployment
python -m deploy.cli deploy-all payment order email --parallel
```

### Monitor Everything

```bash
# View status
python -m deploy.cli status

# View logs
gcloud run services logs read payment-service

# Search by run_id
gcloud logging read 'jsonPayload.run_id="exec_20250113_abc123"'
```

## 💰 Cost Breakdown

| Scenario | Monthly Cost |
|----------|-------------|
| Idle (no traffic) | ~$2-3 |
| 100 req/day | ~$10-15 |
| 10,000 req/day | ~$50-100 |

All services scale to zero - you only pay for what you use!

## 🎓 What's Special

1. **Pure Google Cloud APIs** - No subprocess hacks, proper error handling
2. **Complete Tracing** - Every operation tracked across all services
3. **5-10 Second Builds** - vs 2-3 minutes without base images
4. **Cost-Effective** - Scales to zero, minimal idle costs
5. **Production-Ready** - Monitoring, logging, rollbacks, health checks
6. **Developer-Friendly** - One command to create and deploy services

## 🛠️ Key Commands

```bash
# Create service
python tools/create_service.py <name> --lang python

# Deploy service
python -m deploy.cli deploy <service-name>

# Check status
python -m deploy.cli status

# View services
python -m deploy.cli services

# Rollback
python -m deploy.cli rollback <service> <version>
```

## 📚 Full Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start
- **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Complete 30-min setup
- **[docs/COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** - Full platform guide
- **[COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)** - All CLI commands
- **[FINAL_SUMMARY.md](FINAL_SUMMARY.md)** - What's been built
- **[BUILD_COMPLETE.md](BUILD_COMPLETE.md)** - Build summary

Plus component-specific guides in each directory.

## 🎯 Configuration

**Project**: globalwinner
**Region**: us-east1

All configured and ready to use!

## 🙏 Built With

- Google Cloud Platform (Cloud Run, Cloud Build, Artifact Registry)
- Python 3.11+ (deployment system, SDK)
- Terraform (infrastructure as code)
- FastAPI (Python services)
- Express (Node.js services)
- OpenTelemetry (distributed tracing)

## 📜 License

MIT

---

**Ready to build amazing microservices! 🚀**

*For support, check the documentation in `docs/` or use `--help` on any CLI command.*
