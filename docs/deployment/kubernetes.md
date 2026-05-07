# Kubernetes Deployment

Below is a minimal set of Kubernetes manifests for running the AIO Framework in a cluster.

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aio-framework
  labels:
    app: aio-framework
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aio-framework
  template:
    metadata:
      labels:
        app: aio-framework
    spec:
      containers:
        - name: aio
          image: aio-framework:latest
          command: ["aio", "run", "echo hello world"]
          envFrom:
            - configMapRef:
                name: aio-config
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: aio-secrets
                  key: openai-api-key
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          ports:
            - containerPort: 8000
              name: dashboard
            - containerPort: 9091
              name: metrics
```

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: aio-framework
spec:
  selector:
    app: aio-framework
  ports:
    - name: dashboard
      port: 8000
      targetPort: 8000
    - name: metrics
      port: 9091
      targetPort: 9091
```

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aio-config
data:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.monitoring:4317"
  PROMETHEUS_PORT: "9091"
  ENABLE_PRIORITY_3: "true"
  MCP_ENABLE: "false"
```

## Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aio-secrets
type: Opaque
stringData:
  openai-api-key: "sk-..."
```

## Horizontal Pod Autoscaler (Optional)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aio-framework
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aio-framework
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Notes

- Mount Docker socket via hostPath only if sandbox execution is required (security risk).
- Use a dedicated service account with minimal RBAC permissions.
- Consider running the observability stack (Prometheus, Grafana, Jaeger) in a separate namespace.
