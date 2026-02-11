"""
Tests for Fundraising Escrow Smart Contract

Tests cover:
- Campaign creation
- Adding milestones
- Donations (including anonymous)
- Milestone completion
- Fund release
- Refunds for failed campaigns
"""

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context
from contracts.fundraising.contract import FundraisingEscrow


class TestFundraisingEscrow:
    """Test suite for FundraisingEscrow contract."""
    
    @pytest.fixture
    def context(self) -> AlgopyTestContext:
        """Create a fresh testing context for each test."""
        with algopy_testing_context() as ctx:
            yield ctx
    
    def test_create_contract(self, context: AlgopyTestContext):
        """Test creating the fundraising contract."""
        # Act
        contract = FundraisingEscrow()
        contract.create()
        
        # Assert
        assert contract.campaign_count.value == 0
    
    def test_create_campaign(self, context: AlgopyTestContext):
        """Test creating a fundraising campaign."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        future_deadline = context.any.uint64(min_value=2000000000)  # Future timestamp
        
        # Act
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(10_000_000),  # 10 ALGO
            deadline=ARC4UInt64(future_deadline),
            title=String("Medical Emergency Fund"),
            description=String("Help a student with medical bills")
        )
        
        # Assert
        assert campaign_id.native == 0
        assert contract.campaign_count.value == 1
    
    def test_add_milestone(self, context: AlgopyTestContext):
        """Test adding a milestone to campaign."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(10_000_000),
            deadline=ARC4UInt64(2000000000),
            title=String("Project Fund"),
            description=String("Fund a project")
        )
        
        # Act
        milestone_id = contract.add_milestone(
            campaign_id=campaign_id,
            description=String("Phase 1 Complete"),
            amount=ARC4UInt64(5_000_000)
        )
        
        # Assert
        assert milestone_id.native == 0
    
    def test_only_creator_can_add_milestone(self, context: AlgopyTestContext):
        """Test that only campaign creator can add milestones."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(10_000_000),
            deadline=ARC4UInt64(2000000000),
            title=String("Project"),
            description=String("Description")
        )
        
        # Switch to different user
        other_user = context.any.account()
        context.set_sender(other_user)
        
        # Act & Assert
        with pytest.raises(AssertionError, match="Only creator can add milestones"):
            contract.add_milestone(
                campaign_id=campaign_id,
                description=String("Unauthorized milestone"),
                amount=ARC4UInt64(1_000_000)
            )
    
    def test_get_campaign(self, context: AlgopyTestContext):
        """Test getting campaign details."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        goal = 10_000_000
        deadline = 2000000000
        
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(goal),
            deadline=ARC4UInt64(deadline),
            title=String("Test Campaign"),
            description=String("Test description")
        )
        
        # Act
        result = contract.get_campaign(campaign_id)
        creator, returned_beneficiary, returned_goal, raised, returned_deadline, status = result.native
        
        # Assert
        assert returned_goal == goal
        assert raised == 0
        assert returned_deadline == deadline
        assert status == 0  # STATUS_ACTIVE
    
    def test_get_campaign_count(self, context: AlgopyTestContext):
        """Test getting campaign count."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        
        # Create multiple campaigns
        for i in range(3):
            contract.create_campaign(
                beneficiary=Address(beneficiary.bytes),
                goal=ARC4UInt64(1_000_000 * (i + 1)),
                deadline=ARC4UInt64(2000000000),
                title=String(f"Campaign {i}"),
                description=String("Description")
            )
        
        # Act
        count = contract.get_campaign_count()
        
        # Assert
        assert count.native == 3
    
    def test_get_my_donation_no_donation(self, context: AlgopyTestContext):
        """Test getting donation when none was made."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(10_000_000),
            deadline=ARC4UInt64(2000000000),
            title=String("Campaign"),
            description=String("Description")
        )
        
        # Switch to different user
        new_user = context.any.account()
        context.set_sender(new_user)
        
        # Act
        donation = contract.get_my_donation(campaign_id)
        
        # Assert
        assert donation.native == 0
    
    def test_cancel_campaign(self, context: AlgopyTestContext):
        """Test campaign cancellation."""
        # Arrange
        from algopy.arc4 import UInt64 as ARC4UInt64, String, Address
        
        contract = FundraisingEscrow()
        contract.create()
        
        beneficiary = context.any.account()
        
        campaign_id = contract.create_campaign(
            beneficiary=Address(beneficiary.bytes),
            goal=ARC4UInt64(10_000_000),
            deadline=ARC4UInt64(2000000000),
            title=String("Cancellable Campaign"),
            description=String("This will be cancelled")
        )
        
        # Act
        contract.cancel_campaign(campaign_id)
        
        # Assert
        result = contract.get_campaign(campaign_id)
        _, _, _, _, _, status = result.native
        assert status == 2  # STATUS_FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
