from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def _agent_node(self):
        """The core node logic."""
        pass
    
    @abstractmethod
    def build_agent(self):
        """Build and return the compiled agent graph."""
        pass
    
    @classmethod
    @abstractmethod
    def create_agent(self):
        """Factory method to create and return a compiled agent graph."""
        pass