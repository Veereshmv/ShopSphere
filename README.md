# ShopSphere — E-commerce Microservices on Azure

ShopSphere is a cloud-native e-commerce application built to demonstrate containerization, CI/CD automation, Kubernetes deployment, GitOps-based delivery, and monitoring using Microsoft Azure and open-source DevOps tools.

The project uses a simple HTML and CSS frontend with FastAPI-based backend microservices. Application containers are stored in Azure Container Registry (ACR) and deployed to Azure Kubernetes Service (AKS), with Argo CD managing GitOps-based deployments.

## Architecture

### Application Layer

The following diagram illustrates the ShopSphere CI/CD pipeline,
GitOps deployment workflow, application microservices, data layer,
and monitoring setup.

![ShopSphere Architecture](docs/screenshots/architecture.png)

- **Frontend:** HTML and CSS
- **Product Service:** FastAPI
- **Cart Service:** FastAPI
- **Order Service:** FastAPI
- **Inventory Service:** FastAPI
- **Payment Service:** FastAPI with simulated payment processing

### Data Layer

- **PostgreSQL:** Persistent application data
- **Redis:** Cart data storage

### Cloud and DevOps Tools

| Technology | Purpose |
|---|---|
| Microsoft Azure | Cloud platform |
| Azure Repos | Source code and Kubernetes manifest management |
| Azure DevOps Pipelines | CI automation using YAML |
| Docker | Containerization |
| Azure Container Registry (ACR) | Container image registry |
| Azure Kubernetes Service (AKS) | Container orchestration |
| Argo CD | GitOps-based continuous delivery |
| Prometheus | Metrics collection |
| Grafana | Monitoring dashboards |
| SonarQube | Code quality analysis environment |

## CI/CD and GitOps Workflow

1. **Source Control:** Application source code and Kubernetes manifests are maintained in Azure Repos.
2. **Continuous Integration:** Azure Pipelines executes the configured CI workflow to test application components and build container images.
3. **Container Registry:** Built images are published to Azure Container Registry.
4. **Kubernetes Deployment:** Application services and supporting resources run on Azure Kubernetes Service.
5. **GitOps Delivery:** Argo CD monitors the configured Git repository and applies manifest changes when synchronization is initiated.
6. **Monitoring:** Prometheus collects metrics, and Grafana dashboards visualize infrastructure and CPU utilization.

## Monitoring and Observability

The project includes Prometheus and Grafana for monitoring Kubernetes workloads and node-level CPU utilization.

Grafana dashboards provide visual insights into CPU utilization and help demonstrate basic infrastructure monitoring and troubleshooting.

## Code Quality

SonarQube was set up as part of the project environment for code quality analysis. Its presence in the environment does not imply integration into the CI pipeline unless explicitly configured.

## Screenshots

The following screenshots demonstrate the deployed application and DevOps tooling.

### Application

![ShopSphere Application 1](docs/screenshots/APP_1.png)

![ShopSphere Application 2](docs/screenshots/APP_2.png)

![ShopSphere Application 3](docs/screenshots/APP_3.png)

![ShopSphere Application 4](docs/screenshots/APP_4.png)

### Argo CD — GitOps Deployment

![Argo CD](docs/screenshots/ArgoCD.png)

### Grafana — Monitoring Dashboard

![Grafana](docs/screenshots/Grafana.png)

### SonarQube — Code Quality Environment

![SonarQube](docs/screenshots/SonarQube.png)

## Key Learning Outcomes

- Building and containerizing a multi-service web application.
- Configuring Azure DevOps YAML pipelines for CI.
- Publishing container images to Azure Container Registry.
- Deploying and troubleshooting workloads on AKS.
- Managing Kubernetes deployments through Argo CD.
- Understanding GitOps synchronization and deployment updates.
- Monitoring node CPU utilization using Prometheus and Grafana.
- Troubleshooting Kubernetes scheduling and scaling issues.

## Repository

**GitHub:** https://github.com/Veereshmv/ShopSphere

## Disclaimer

ShopSphere is a portfolio and learning project intended to demonstrate cloud, containerization, CI/CD, GitOps, and monitoring concepts. It is not presented as a production e-commerce platform.
