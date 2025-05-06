"""
Global Observer for Distributed Swarm RL.

Collects, aggregates, and potentially logs or exposes metrics from all participating
agent nodes in a distributed training session.

Responsibilities:
- Receive metric updates from individual nodes (via CommunicationBus).
- Aggregate metrics (e.g., average rewards, episode lengths, success rates).
- Store or expose aggregated metrics for monitoring or analysis.
- Potentially trigger alerts or actions based on observed metrics.
"""

import asyncio
from typing import Dict, Any, List
from collections import defaultdict
import time

class GlobalObserver:
    def __init__(self, config: Dict[str, Any] = None):
        """Initializes the Global Observer.

        Args:
            config: Optional configuration for the observer (e.g., aggregation methods, logging targets).
        """
        self.config = config or {}
        self.metrics = defaultdict(lambda: defaultdict(list)) # E.g., metrics[agent_id][metric_name] = [values]
        self.last_update_time = time.time()
        print("GlobalObserver initialized.")

    async def record_metric(self, node_id: str, metric_data: Dict[str, Any]):
        """Records metrics received from a specific node.

        Args:
            node_id: The identifier of the node reporting the metrics.
            metric_data: A dictionary containing metric names and values.
                       Example: {'reward': 1.5, 'episode_length': 100}
        """
        timestamp = time.time()
        print(f"Received metrics from {node_id}: {metric_data}")
        for metric_name, value in metric_data.items():
            self.metrics[node_id][metric_name].append(value)
        self.last_update_time = timestamp

    def get_aggregated_metrics(self, aggregation_window: float = 60.0) -> Dict[str, Any]:
        """Calculates and returns aggregated metrics over a time window or all data.

        Args:
            aggregation_window: Time window in seconds for aggregation (if needed, currently unused).

        Returns:
            A dictionary containing aggregated metrics (e.g., average reward per agent).
        """
        aggregated = defaultdict(dict)
        print("Calculating aggregated metrics...")
        for node_id, node_metrics in self.metrics.items():
            for metric_name, values in node_metrics.items():
                if values:
                    # Simple aggregation: Average
                    avg_value = sum(values) / len(values)
                    aggregated[node_id][f"{metric_name}_avg"] = avg_value
                    aggregated[node_id][f"{metric_name}_count"] = len(values)
                    # TODO: Add more aggregation types (min, max, stddev, sum)

        aggregated['overall']['last_update'] = self.last_update_time
        aggregated['overall']['reporting_nodes'] = list(self.metrics.keys())
        print(f"Aggregated metrics: {aggregated}")
        return dict(aggregated) # Convert back to regular dict

    # Placeholder for potential methods to push metrics to a dashboard or logging system
    async def report_metrics(self):
        """Periodically reports or logs aggregated metrics."""
        while True:
            await asyncio.sleep(self.config.get('report_interval', 60)) # Default report every 60s
            metrics_snapshot = self.get_aggregated_metrics()
            print(f"Reporting metrics snapshot: {metrics_snapshot}")
            # TODO: Implement actual reporting (e.g., push to Prometheus, log to file)

# Example usage (placeholder)
async def main():
    observer = GlobalObserver()
    # Simulate receiving metrics
    await observer.record_metric('node1', {'reward': 1.0, 'steps': 50})
    await observer.record_metric('node2', {'reward': 1.5, 'steps': 60})
    await observer.record_metric('node1', {'reward': 0.5, 'steps': 45})

    agg_metrics = observer.get_aggregated_metrics()
    # print(agg_metrics)

    # Start reporting loop (won't exit in this example)
    # asyncio.create_task(observer.report_metrics())
    # await asyncio.sleep(120)

if __name__ == "__main__":
    # asyncio.run(main())
    print("Global Observer scaffold created. Run main() for example usage.") 