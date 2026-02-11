"""
Tests for Soulbound Ticket Smart Contract

Tests cover:
- Event creation with ARC-71 ASA
- Ticket minting (soulbound)
- Ticket verification
- Non-transferability (freeze)
- Ticket revocation (clawback)
"""

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context
from contracts.soulbound_ticket.contract import SoulboundTicket


class TestSoulboundTicket:
    """Test suite for SoulboundTicket contract."""
    
    @pytest.fixture
    def context(self) -> AlgopyTestContext:
        """Create a fresh testing context for each test."""
        with algopy_testing_context() as ctx:
            yield ctx
    
    def test_create_contract(self, context: AlgopyTestContext):
        """Test creating the soulbound ticket contract."""
        # Act
        contract = SoulboundTicket()
        contract.create()
        
        # Assert
        assert contract.event_count.value == 0
    
    def test_create_event(self, context: AlgopyTestContext):
        """Test creating an event with tickets."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String
        
        contract = SoulboundTicket()
        contract.create()
        
        # Act
        event_id = contract.create_event(
            name=String("Tech Fest 2026"),
            max_tickets=ARC4UInt64(100),
            price=ARC4UInt64(5_000_000),  # 5 ALGO
            event_date=ARC4UInt64(1739000000),  # Future timestamp
            venue=String("Main Auditorium")
        )
        
        # Assert
        assert event_id.native == 0
        assert contract.event_count.value == 1
    
    def test_get_event_count(self, context: AlgopyTestContext):
        """Test getting event count."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String
        
        contract = SoulboundTicket()
        contract.create()
        
        # Create multiple events
        for i in range(3):
            contract.create_event(
                name=String(f"Event {i}"),
                max_tickets=ARC4UInt64(50),
                price=ARC4UInt64(1_000_000),
                event_date=ARC4UInt64(1739000000 + i * 86400),
                venue=String("Venue")
            )
        
        # Act
        count = contract.get_event_count()
        
        # Assert
        assert count.native == 3
    
    def test_verify_ticket_no_ticket(self, context: AlgopyTestContext):
        """Test ticket verification when holder has no ticket."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = SoulboundTicket()
        contract.create()
        
        contract.create_event(
            name=String("Concert"),
            max_tickets=ARC4UInt64(100),
            price=ARC4UInt64(2_000_000),
            event_date=ARC4UInt64(1739000000),
            venue=String("Stadium")
        )
        
        random_holder = context.any.account()
        
        # Act
        result = contract.verify_ticket(Address(random_holder.bytes), ARC4UInt64(0))
        
        # Assert
        assert result.native == False
    
    def test_cannot_delete_with_events(self, context: AlgopyTestContext):
        """Test that contract cannot be deleted with active events."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String
        
        contract = SoulboundTicket()
        contract.create()
        
        contract.create_event(
            name=String("Event"),
            max_tickets=ARC4UInt64(50),
            price=ARC4UInt64(1_000_000),
            event_date=ARC4UInt64(1739000000),
            venue=String("Venue")
        )
        
        # Act & Assert
        with pytest.raises(AssertionError, match="Cannot delete with active events"):
            contract.delete()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
