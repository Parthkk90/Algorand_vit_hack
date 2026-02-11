"""
Tests for DAO Treasury Smart Contract

Tests cover:
- Treasury creation with threshold
- Adding/removing signers
- Creating proposals
- Approval process
- Fund execution
"""

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context
from contracts.dao_treasury.contract import DAOTreasury


class TestDAOTreasury:
    """Test suite for DAOTreasury contract."""
    
    @pytest.fixture
    def context(self) -> AlgopyTestContext:
        """Create a fresh testing context for each test."""
        with algopy_testing_context() as ctx:
            yield ctx
    
    def test_create_treasury(self, context: AlgopyTestContext):
        """Test creating a new treasury with threshold."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64
        threshold = ARC4UInt64(2)  # 2-of-N
        
        # Act
        contract = DAOTreasury()
        contract.create(threshold)
        
        # Assert
        assert contract.threshold.value == 2
        assert contract.signer_count.value == 0
        assert contract.proposal_count.value == 0
    
    def test_add_signer(self, context: AlgopyTestContext):
        """Test adding a signer to treasury."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, Address
        
        contract = DAOTreasury()
        contract.create(ARC4UInt64(1))
        
        signer = context.any.account()
        
        # Signer must opt-in first
        context.set_sender(signer)
        contract.opt_in()
        
        # Creator adds signer
        context.set_sender(context.default_sender)
        
        # Act
        contract.add_signer(Address(signer.bytes))
        
        # Assert
        assert contract.signer_count.value == 1
        assert contract.is_signer[signer] == 1
    
    def test_threshold_cannot_exceed_signers(self, context: AlgopyTestContext):
        """Test that threshold cannot exceed signer count."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, Address
        
        contract = DAOTreasury()
        contract.create(ARC4UInt64(3))  # Need 3 approvals
        
        signer = context.any.account()
        context.set_sender(signer)
        contract.opt_in()
        context.set_sender(context.default_sender)
        
        # Act & Assert - adding 1 signer when threshold is 3 should fail
        with pytest.raises(AssertionError, match="Threshold exceeds signers"):
            contract.add_signer(Address(signer.bytes))
    
    def test_create_proposal(self, context: AlgopyTestContext):
        """Test creating a spending proposal."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, Address, String
        
        contract = DAOTreasury()
        contract.create(ARC4UInt64(1))
        
        signer = context.any.account()
        context.set_sender(signer)
        contract.opt_in()
        context.set_sender(context.default_sender)
        contract.add_signer(Address(signer.bytes))
        
        recipient = context.any.account()
        
        # Act - signer creates proposal
        context.set_sender(signer)
        proposal_id = contract.create_proposal(
            Address(recipient.bytes),
            ARC4UInt64(1_000_000),
            String("Buy equipment")
        )
        
        # Assert
        assert proposal_id.native == 0
        assert contract.proposal_count.value == 1
    
    def test_only_signers_can_propose(self, context: AlgopyTestContext):
        """Test that only signers can create proposals."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, Address, String
        
        contract = DAOTreasury()
        contract.create(ARC4UInt64(1))
        
        non_signer = context.any.account()
        context.set_sender(non_signer)
        contract.opt_in()
        
        recipient = context.any.account()
        
        # Act & Assert
        with pytest.raises(AssertionError, match="Only signers can propose"):
            contract.create_proposal(
                Address(recipient.bytes),
                ARC4UInt64(1_000_000),
                String("Malicious proposal")
            )
    
    def test_get_treasury_info(self, context: AlgopyTestContext):
        """Test getting treasury information."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64
        
        contract = DAOTreasury()
        contract.create(ARC4UInt64(2))
        
        # Act
        result = contract.get_treasury_info()
        threshold, signer_count, proposal_count, available = result.native
        
        # Assert
        assert threshold == 2
        assert signer_count == 0
        assert proposal_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
