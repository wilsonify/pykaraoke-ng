#!/usr/bin/env bash
#
# Kubernetes-in-Docker (kind) helper script for PyKaraoke-NG
#
# Usage:
#   ./scripts/kind-setup.sh create    # Create cluster and deploy
#   ./scripts/kind-setup.sh delete    # Delete cluster
#   ./scripts/kind-setup.sh deploy    # Deploy to existing cluster
#   ./scripts/kind-setup.sh test      # Run tests in cluster
#   ./scripts/kind-setup.sh status    # Show cluster status
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="pykaraoke"
IMAGE_NAME="pykaraoke-ng:latest"

# Check if kind is installed
check_kind() {
    if ! command -v kind >/dev/null 2>&1; then
        echo -e "${RED}Error: kind is not installed.${NC}"
        echo "Install with: go install sigs.k8s.io/kind@latest"
        echo "Or: brew install kind"
        exit 1
    fi
}

# Check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl >/dev/null 2>&1; then
        echo -e "${RED}Error: kubectl is not installed.${NC}"
        exit 1
    fi
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running.${NC}"
        exit 1
    fi
}

# Create the kind cluster
create_cluster() {
    echo -e "${BLUE}Creating kind cluster: $CLUSTER_NAME${NC}"
    
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        echo -e "${YELLOW}Cluster $CLUSTER_NAME already exists.${NC}"
        return 0
    fi
    
    kind create cluster \
        --name "$CLUSTER_NAME" \
        --config "$ROOT_DIR/k8s/kind-config.yaml" \
        --wait 60s
    
    echo -e "${GREEN}✓ Cluster created successfully${NC}"
}

# Delete the kind cluster
delete_cluster() {
    echo -e "${BLUE}Deleting kind cluster: $CLUSTER_NAME${NC}"
    kind delete cluster --name "$CLUSTER_NAME" || true
    echo -e "${GREEN}✓ Cluster deleted${NC}"
}

# Build and load image into kind
build_and_load() {
    echo -e "${BLUE}Building Docker image...${NC}"
    docker build -t "$IMAGE_NAME" "$ROOT_DIR"
    
    echo -e "${BLUE}Loading image into kind cluster...${NC}"
    kind load docker-image "$IMAGE_NAME" --name "$CLUSTER_NAME"
    
    echo -e "${GREEN}✓ Image loaded into cluster${NC}"
}

# Deploy to the cluster
deploy() {
    echo -e "${BLUE}Deploying PyKaraoke-NG to cluster...${NC}"
    
    # Create namespace
    kubectl apply -f "$ROOT_DIR/k8s/namespace.yaml"
    
    # Apply deployment
    kubectl apply -f "$ROOT_DIR/k8s/deployment.yaml"
    
    # Wait for deployment
    echo -e "${BLUE}Waiting for deployment to be ready...${NC}"
    kubectl -n pykaraoke rollout status deployment/pykaraoke-ng --timeout=120s || true
    
    echo -e "${GREEN}✓ Deployment complete${NC}"
}

# Run tests in the cluster
run_tests() {
    echo -e "${BLUE}Running tests in cluster...${NC}"
    
    # Build test image
    docker build -t pykaraoke-ng:test --target test "$ROOT_DIR"
    kind load docker-image pykaraoke-ng:test --name "$CLUSTER_NAME"
    
    # Run tests as a Job
    kubectl -n pykaraoke delete job pykaraoke-test 2>/dev/null || true
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: pykaraoke-test
  namespace: pykaraoke
spec:
  ttlSecondsAfterFinished: 300
  template:
    spec:
      containers:
      - name: test
        image: pykaraoke-ng:test
        command: ["pytest", "tests/", "-v", "--tb=short"]
      restartPolicy: Never
  backoffLimit: 1
EOF
    
    echo -e "${BLUE}Waiting for tests to complete...${NC}"
    kubectl -n pykaraoke wait --for=condition=complete job/pykaraoke-test --timeout=300s || \
    kubectl -n pykaraoke wait --for=condition=failed job/pykaraoke-test --timeout=300s
    
    # Show logs
    kubectl -n pykaraoke logs job/pykaraoke-test
}

# Show cluster status
show_status() {
    echo -e "${BLUE}Cluster Status${NC}"
    echo "=============="
    
    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        echo -e "${YELLOW}Cluster $CLUSTER_NAME does not exist.${NC}"
        return 0
    fi
    
    echo ""
    echo "Nodes:"
    kubectl get nodes -o wide
    
    echo ""
    echo "Pods in pykaraoke namespace:"
    kubectl -n pykaraoke get pods -o wide 2>/dev/null || echo "Namespace not found"
    
    echo ""
    echo "Services:"
    kubectl -n pykaraoke get services 2>/dev/null || echo "No services"
}

# Main
main() {
    check_docker
    check_kind
    check_kubectl
    
    case "${1:-help}" in
        create)
            create_cluster
            build_and_load
            deploy
            show_status
            ;;
        delete)
            delete_cluster
            ;;
        deploy)
            build_and_load
            deploy
            ;;
        test)
            run_tests
            ;;
        status)
            show_status
            ;;
        build)
            build_and_load
            ;;
        help|--help|-h)
            echo "Usage: $0 {create|delete|deploy|test|status|build}"
            echo ""
            echo "Commands:"
            echo "  create  - Create cluster and deploy application"
            echo "  delete  - Delete the kind cluster"
            echo "  deploy  - Deploy to existing cluster"
            echo "  test    - Run tests in cluster"
            echo "  status  - Show cluster status"
            echo "  build   - Build and load image into cluster"
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            exit 1
            ;;
    esac
}

main "$@"
