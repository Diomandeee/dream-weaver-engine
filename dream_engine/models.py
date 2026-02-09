"""Dream data models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class DreamStage(str, Enum):
    SEED = "seed"
    GERMINATING = "germinating"
    GROWING = "growing"
    FLOWERING = "flowering"
    BLOOM = "bloom"
    ARCHIVED = "archived"


class Dream(BaseModel):
    """A dream in the garden."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    essence: str  # Core idea
    context: str = ""  # Additional context
    strength: float = 0.1  # 0.0 - 1.0
    stage: DreamStage = DreamStage.SEED
    
    # Evolution tracking
    evolution_count: int = 0
    last_evolved: Optional[datetime] = None
    connections: list[str] = Field(default_factory=list)  # IDs of related dreams
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"  # manual, import, cross-pollination
    
    # Evolution history
    evolution_notes: list[str] = Field(default_factory=list)
    
    def get_stage(self) -> DreamStage:
        """Determine stage based on strength."""
        if self.strength < 0.2:
            return DreamStage.SEED
        elif self.strength < 0.4:
            return DreamStage.GERMINATING
        elif self.strength < 0.6:
            return DreamStage.GROWING
        elif self.strength < 0.8:
            return DreamStage.FLOWERING
        else:
            return DreamStage.BLOOM
    
    def update_stage(self):
        """Update stage based on current strength."""
        self.stage = self.get_stage()
    
    def to_prompt_context(self) -> str:
        """Format dream for LLM context."""
        return f"""## {self.title}
**Essence:** {self.essence}
**Context:** {self.context}
**Strength:** {self.strength:.2f}
**Stage:** {self.stage.value}
**Tags:** {', '.join(self.tags) if self.tags else 'none'}
**Connections:** {', '.join(self.connections) if self.connections else 'none'}
**Evolutions:** {self.evolution_count}
"""


class GardenState(BaseModel):
    """Overall garden state."""
    
    dreams: dict[str, Dream] = Field(default_factory=dict)
    last_evolution: Optional[datetime] = None
    total_evolutions: int = 0
    total_blooms: int = 0
    
    def add_dream(self, dream: Dream):
        """Add a dream to the garden."""
        self.dreams[dream.id] = dream
    
    def get_dreams_for_evolution(self, max_count: int = 5) -> list[Dream]:
        """Get dreams ready for evolution, prioritizing lower strength."""
        active = [d for d in self.dreams.values() if d.stage != DreamStage.ARCHIVED]
        # Sort by strength (evolve weaker dreams first) and last_evolved
        sorted_dreams = sorted(active, key=lambda d: (d.strength, d.last_evolved or datetime.min))
        return sorted_dreams[:max_count]
    
    def get_potential_connections(self, dream: Dream, max_count: int = 3) -> list[Dream]:
        """Find dreams that could cross-pollinate with this one."""
        others = [d for d in self.dreams.values() 
                  if d.id != dream.id and d.stage != DreamStage.ARCHIVED]
        # Could add semantic similarity here later
        return others[:max_count]
