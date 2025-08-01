"""
SK-603: Grafana Dashboard Generator for Advanced Caching Metrics

This script generates a Grafana dashboard configuration in JSON format.
The dashboard is designed to monitor the advanced caching system implemented in SK-603.

Usage:
    python dashboard/grafana_dashboard_generator.py > sk603_cache_dashboard.json

The output JSON file can be imported directly into Grafana.
"""

import json

def generate_dashboard():
    """Generates the Grafana dashboard configuration."""

    dashboard = {
        "__inputs": [],
        "__requires": [
            {
                "type": "grafana",
                "id": "grafana",
                "name": "Grafana",
                "version": "7.5.0"
            },
            {
                "type": "datasource",
                "id": "prometheus",
                "name": "Prometheus",
                "version": "1.0.0"
            }
        ],
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": "-- Grafana --",
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "links": [],
        "liveNow": False,
        "panels": [
            # Panel 1: Cache Hit Rate
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {"axisCenteredZero": False, "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 0, "gradientMode": "none", "hideFrom": {"legend": False, "tooltip": False, "viz": False}, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "scaleDistribution": {"type": "linear"}, "showPoints": "auto", "spanNulls": False, "stacking": {"group": "A", "mode": "none"}, "thresholdsStyle": {"mode": "off"}},
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 80}]},
                        "unit": "percent"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "id": 2,
                "options": {"legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "single"}},
                "targets": [
                    {
                        "expr": 'sum(rate(cache_hits_total{job="senangkira"}[5m])) / sum(rate(cache_operations_total{job="senangkira"}[5m])) * 100',
                        "legendFormat": "Total Cache Hit Rate",
                        "refId": "A"
                    },
                    {
                        "expr": 'sum(rate(cache_hits_total{job="senangkira", level="L1"}[5m])) / sum(rate(cache_operations_total{job="senangkira", level="L1"}[5m])) * 100',
                        "legendFormat": "L1 Memory Cache Hit Rate",
                        "refId": "B"
                    },
                    {
                        "expr": 'sum(rate(cache_hits_total{job="senangkira", level="L2"}[5m])) / sum(rate(cache_operations_total{job="senangkira", level="L2"}[5m])) * 100',
                        "legendFormat": "L2 Redis Cache Hit Rate",
                        "refId": "C"
                    }
                ],
                "title": "Cache Hit Rate",
                "type": "graph"
            },

            # Panel 2: Average Cache Response Time
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {"axisCenteredZero": False, "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 0, "gradientMode": "none", "hideFrom": {"legend": False, "tooltip": False, "viz": False}, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "scaleDistribution": {"type": "linear"}, "showPoints": "auto", "spanNulls": False, "stacking": {"group": "A", "mode": "none"}, "thresholdsStyle": {"mode": "off"}},
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 100}, {"color": "red", "value": 200}]},
                        "unit": "ms"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "id": 4,
                "options": {"legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "single"}},
                "targets": [
                    {
                        "expr": 'rate(cache_response_time_sum{job="senangkira"}[5m]) / rate(cache_response_time_count{job="senangkira"}[5m])',
                        "legendFormat": "Avg Response Time",
                        "refId": "A"
                    },
                    {
                        "expr": 'histogram_quantile(0.95, sum(rate(cache_response_time_bucket{job="senangkira"}[5m])) by (le))',
                        "legendFormat": "P95 Response Time",
                        "refId": "B"
                    }
                ],
                "title": "Cache Response Time (Avg & P95)",
                "type": "graph"
            },
            
            # Panel 3: Cache Memory Usage
            {
                "datasource": "prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "id": 6,
                "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "showThresholdLabels": False, "showThresholdMarkers": True},
                "pluginVersion": "7.5.0",
                "targets": [
                    {
                        "expr": 'sum(cache_memory_usage_bytes{job="senangkira"}) by (level)',
                        "legendFormat": "{{level}} Memory Usage",
                        "refId": "A"
                    }
                ],
                "title": "Cache Memory Usage",
                "type": "gauge",
                "fieldConfig": {
                    "defaults": {
                        "unit": "bytes"
                    }
                }
            },
            
            # Panel 4: Cache Pattern Usage
            {
                "datasource": "prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "id": 8,
                "options": {"legend": {"displayMode": "list", "placement": "right"}, "pieType": "pie", "reduceOptions": {"calcs": ["sum"], "fields": "", "values": False}},
                "pluginVersion": "7.5.0",
                "targets": [
                    {
                        "expr": 'sum(rate(cache_pattern_usage_total{job="senangkira"}[5m])) by (pattern)',
                        "legendFormat": "{{pattern}}",
                        "refId": "A"
                    }
                ],
                "title": "Cache Pattern Usage",
                "type": "piechart"
            },
            
            # Panel 5: Cache Security Alerts
            {
                "datasource": "prometheus",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16},
                "id": 10,
                "options": {"showHeaders": True, "sortBy": [{"displayName": "Time", "desc": True}]},
                "targets": [
                    {
                        "expr": 'ALERTS{alertname="CacheSecurityAlert", job="senangkira"}',
                        "legendFormat": "",
                        "refId": "A"
                    }
                ],
                "title": "Cache Security Alerts",
                "type": "table"
            },
            
            # Panel 6: Celery Worker Count
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "orange", "value": 1},
                                {"color": "green", "value": 2}
                            ]
                        },
                        "unit": "none"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 24},
                "id": 12,
                "options": {
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "showThresholdLabels": False,
                    "showThresholdMarkers": True
                },
                "pluginVersion": "7.5.0",
                "targets": [
                    {
                        "expr": 'celery_workers_count{job="senangkira"}',
                        "legendFormat": "Active Workers",
                        "refId": "A"
                    }
                ],
                "title": "Active Celery Workers",
                "type": "gauge"
            },
            
            # Panel 7: Celery Queue Backlog
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisLabel": "",
                            "axisPlacement": "auto",
                            "barAlignment": 0,
                            "drawStyle": "line",
                            "fillOpacity": 10,
                            "gradientMode": "none",
                            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                            "lineInterpolation": "linear",
                            "lineWidth": 1,
                            "pointSize": 5,
                            "scaleDistribution": {"type": "linear"},
                            "showPoints": "never",
                            "spanNulls": True
                        },
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                        "unit": "short"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 18, "x": 6, "y": 24},
                "id": 14,
                "options": {
                    "legend": {"calcs": ["mean", "lastNotNull", "max"], "displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi"}
                },
                "targets": [
                    {
                        "expr": 'celery_queues_backlog{job="senangkira"}',
                        "legendFormat": "{{queue}}",
                        "refId": "A"
                    }
                ],
                "title": "Celery Queue Backlog",
                "type": "timeseries"
            },
            
            # Panel 8: Celery Task Throughput
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisLabel": "",
                            "axisPlacement": "auto",
                            "barAlignment": 0,
                            "drawStyle": "bars",
                            "fillOpacity": 100,
                            "gradientMode": "none",
                            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                            "lineInterpolation": "linear",
                            "lineWidth": 1,
                            "pointSize": 5,
                            "scaleDistribution": {"type": "linear"},
                            "showPoints": "never",
                            "spanNulls": False
                        },
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                        "unit": "short"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 32},
                "id": 16,
                "options": {
                    "legend": {"calcs": ["sum"], "displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi"}
                },
                "targets": [
                    {
                        "expr": 'increase(celery_tasks_total{job="senangkira"}[5m])',
                        "legendFormat": "{{status}}",
                        "refId": "A"
                    }
                ],
                "title": "Celery Task Throughput (5m rate)",
                "type": "timeseries"
            },
            
            # Panel 9: Celery Task Duration
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisLabel": "",
                            "axisPlacement": "auto",
                            "barAlignment": 0,
                            "drawStyle": "line",
                            "fillOpacity": 10,
                            "gradientMode": "none",
                            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                            "lineInterpolation": "linear",
                            "lineWidth": 1,
                            "pointSize": 5,
                            "scaleDistribution": {"type": "linear"},
                            "showPoints": "never",
                            "spanNulls": True
                        },
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                        "unit": "s"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 32},
                "id": 18,
                "options": {
                    "legend": {"calcs": ["mean", "max"], "displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi"}
                },
                "targets": [
                    {
                        "expr": 'histogram_quantile(0.95, sum(rate(celery_task_duration_seconds_bucket{job="senangkira"}[5m])) by (le, queue))',
                        "legendFormat": "{{queue}} P95",
                        "refId": "A"
                    },
                    {
                        "expr": 'histogram_quantile(0.50, sum(rate(celery_task_duration_seconds_bucket{job="senangkira"}[5m])) by (le, queue))',
                        "legendFormat": "{{queue}} Median",
                        "refId": "B"
                    }
                ],
                "title": "Celery Task Duration (P95 & Median)",
                "type": "timeseries"
            },
            
            # Panel 10: Celery Task Errors
            {
                "datasource": "prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "hideFrom": {"legend": False, "tooltip": False, "viz": False}
                        },
                        "mappings": [],
                        "unit": "short"
                    },
                    "overrides": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 40},
                "id": 20,
                "options": {
                    "legend": {"displayMode": "list", "placement": "right"},
                    "pieType": "pie",
                    "reduceOptions": {"calcs": ["sum"], "fields": "", "values": False}
                },
                "targets": [
                    {
                        "expr": 'sum(increase(celery_task_errors_total{job="senangkira"}[1h])) by (error_type)',
                        "legendFormat": "{{error_type}}",
                        "refId": "A"
                    }
                ],
                "title": "Celery Task Errors (Last Hour)",
                "type": "piechart"
            }
        ],
        "refresh": "1m",
        "schemaVersion": 27,
        "style": "dark",
        "tags": ["caching", "celery", "sk-603", "sk-701", "performance"],
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-6h",
            "to": "now"
        },
        "timepicker": {},
        "timezone": "browser",
        "title": "SK-603 & SK-701: Advanced Cache & Celery Performance Dashboard",
        "uid": "sk603-sk701-performance-dashboard",
        "version": 1
    }
    
    return dashboard

if __name__ == "__main__":
    dashboard_json = generate_dashboard()
    print(json.dumps(dashboard_json, indent=4))
