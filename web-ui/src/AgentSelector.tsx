import { useEffect, useState } from 'react';

interface Agent {
  name: string;
  description: string;
  capabilities: string[];
  created: string;
  last_used: string;
}

interface AgentSelectorProps {
  selectedAgent: string;
  onAgentChange: (agentName: string) => void;
  disabled: boolean;
}

export function AgentSelector({
  selectedAgent,
  onAgentChange,
  disabled
}: AgentSelectorProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`http://${window.location.hostname}:8000/api/agents`);
        if (!response.ok) {
          throw new Error('Failed to fetch agents');
        }
        const data = await response.json();
        setAgents(data.agents);
        setError(null);
      } catch (err) {
        console.error('Error fetching agents:', err);
        setError(err instanceof Error ? err.message : 'Failed to load agents');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAgents();
  }, []);

  if (isLoading) {
    return <div className="agent-selector loading">Loading agents...</div>;
  }

  if (error) {
    return <div className="agent-selector error">Error loading agents</div>;
  }

  if (agents.length === 0) {
    return <div className="agent-selector error">No agents found</div>;
  }

  return (
    <select
      value={selectedAgent}
      onChange={(e) => onAgentChange(e.target.value)}
      disabled={disabled}
      className="agent-selector"
      title={agents.find(a => a.name === selectedAgent)?.description}
    >
      {agents.map((agent) => (
        <option key={agent.name} value={agent.name}>
          {agent.name}
        </option>
      ))}
    </select>
  );
}
